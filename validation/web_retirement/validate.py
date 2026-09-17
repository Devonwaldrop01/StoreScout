"""Retained-image shutdown experiments. No production access."""
import concurrent.futures,json,os,pathlib,subprocess,time,traceback
ROOT=pathlib.Path(__file__).resolve().parent
OUT=pathlib.Path(os.environ['RUNNER_TEMP'])/'retirement-evidence';OUT.mkdir(exist_ok=True)
IMAGE='sha256:bd54189c67f7ce0154b0c1ca8bd21b2f57f4bab0f18eb5e8e55b995ea155f0c9'
def run(*args,timeout=120):
 p=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
 if p.returncode:raise RuntimeError((args[:4],p.returncode,p.stdout[-1000:],p.stderr[-1000:]))
 return p.stdout.strip()
def docker(*args,**kw):return run('docker',*args,**kw)
def info(n):return json.loads(docker('inspect',n))[0]
def logs(n):
 p=subprocess.run(['docker','logs','--timestamps',n],capture_output=True,text=True);return p.stdout+p.stderr
def events(n):return [json.loads(x.split('DRAIN_EVENT ',1)[1]) for x in logs(n).splitlines() if 'DRAIN_EVENT ' in x]
def waitfor(f,seconds=35):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  if f():return
  time.sleep(.2)
 raise AssertionError('condition timeout')
def trial(case):
 name='retirement-'+case['name'];r={'case':case,'passed':False};proc=None;observer=None;observer_file=None
 try:
  docker('run','-d','--name',name,'--network','none','--read-only',
   '-e','PORT=10000','-e','PYTHONDONTWRITEBYTECODE=1','-e','PYTHONPATH=/validation',
   '-e','SUPABASE_URL=http://127.0.0.1:19991','-e','SUPABASE_SERVICE_ROLE_KEY=synthetic-only',
   '-e','REDIS_URL=rediss://127.0.0.1:19992/0?ssl_cert_reqs=required&ssl_check_hostname=true',
   '-e','FIXTURE_DURATIONS='+','.join(map(str,case['durations'])),
   '-v',str(ROOT/'sitecustomize.py')+':/validation/sitecustomize.py:ro',IMAGE,
   'uvicorn','app.main:app','--host','0.0.0.0','--port','10000')
  waitfor(lambda:'Application startup complete' in logs(name) and any(e['event']=='fixture_ready' for e in events(name)))
  probe='import http.client,json,time;c=http.client.HTTPConnection("127.0.0.1",10000,timeout=50);c.request("POST","/api/v1/competitors/discover-ai",body=json.dumps({"description":"++++++++++"}),headers={"Content-Type":"application/json"});r=c.getresponse();print(json.dumps({"status":r.status,"body":r.read().decode(),"wall":time.time()}));c.close()'
  proc=subprocess.Popen(['docker','exec',name,'python','-ISB','-c',probe],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
  waitfor(lambda:len([e for e in events(name) if e['event']=='verify_start'])==len(case['durations']))
  if case.get('early'):
   time.sleep(1)
  else:
   waitfor(lambda:any(e['event']=='request_finished' for e in events(name)),25)
   assert len([e for e in events(name) if e['event']=='request_verification_timeout'])==len(case['durations'])
  assert not any(e['event']=='verify_complete' for e in events(name))
  r['process_before_term']=docker('top',name,'-eo','pid,ppid,comm')
  assert len(r['process_before_term'].splitlines())<= (3 if case.get('early') else 2), r['process_before_term']
  # The extra docker-exec HTTP probe process is fixture-only and may still be present in the early case.
  if case.get('observer'):
   host_pid=info(name)['State']['Pid'];r['observed_host_pid']=host_pid
   observer_path=OUT/(case['name']+'-observer.jsonl')
   observer_file=observer_path.open('w')
   observer=subprocess.Popen(['sudo','python3','-IB',str(ROOT/'exit_observer.py'),str(host_pid)],stdout=observer_file,stderr=subprocess.STDOUT)
   waitfor(lambda:'"event": "attached"' in observer_path.read_text(),5)
  r['term_sent_wall']=time.time();docker('kill','--signal','SIGTERM',name)
  waitfor(lambda:any(e['event']=='term_received' for e in events(name)))
  time.sleep(1)
  assert info(name)['State']['Running'], 'process exited with outstanding executor work'
  if case.get('force'):
   time.sleep(29)
   r['forced_kill_wall']=time.time();docker('kill','--signal','SIGKILL',name)
  window=case.get('shutdown_window',40)
  remaining=window-(time.time()-r['term_sent_wall'])
  try:
   code=int(docker('wait',name,timeout=max(1,remaining)))
  except subprocess.TimeoutExpired:
   r['deadline_forced_kill_wall']=time.time();docker('kill','--signal','SIGKILL',name)
   raise AssertionError('shutdown exceeded proposed window; test container forced down')
  r['exit_observed_wall']=time.time();r['exit']=code
  r['seconds_from_term_to_exit']=r['exit_observed_wall']-r['term_sent_wall']
  if not case.get('force'):assert r['seconds_from_term_to_exit']<window
  if observer:
   assert observer.wait(timeout=5)==0
   observer_file.close();observer_file=None
   r['observer_events']=[json.loads(line) for line in observer_path.read_text().splitlines()]
   terminal=[e for e in r['observer_events'] if e['event']=='terminal']
   assert len(terminal)==1 and all(e['pid']==host_pid for e in r['observer_events'])
   assert terminal[0]['signal']==(9 if case.get('force') else None)
   assert terminal[0]['exit_code']==(None if case.get('force') else 0)
  r['state']=info(name)['State'];r['events']=events(name)
  e=r['events'];completed=[x for x in e if x['event']=='verify_complete'];final=[x for x in e if x['event']=='interpreter_atexit']
  assert not any(x['event'] in ('forbidden_operation','fixture_queue_dispatch') for x in e)
  assert all(x['daemon'] is False for x in e if x['event']=='verify_start')
  term=next(x['wall'] for x in e if x['event']=='term_received')
  assert any(x['event']=='executor_activity' and x['wall']>term for x in e)
  if case.get('force'):
   assert code==137 and not completed and not final
   assert 'Finished server process' in logs(name), 'negative control must show misleading early Uvicorn completion log'
  else:
   assert code==0 and len(completed)==len(case['durations']) and len(final)==1
   assert max(x['wall'] for x in completed)<final[0]['wall']<=r['exit_observed_wall']
   assert final[0]['violations']==[]
   assert all(not t['alive'] or t['name']=='MainThread' for t in final[0]['threads'])
   assert any(x['event']=='executor_shutdown_end' for x in e)
  r['passed']=True
 except Exception:
  r['error']=traceback.format_exc();r['diagnostic_log_tail']=logs(name)[-4000:]
 finally:
  if observer and observer.poll() is None:
   # No EXITKILL: ending a failed test observer does not kill its target.
   observer.terminate();observer.wait(timeout=5)
  if observer_file:observer_file.close()
  if proc:
   try:r['http_stdout'],r['http_stderr']=proc.communicate(timeout=5)
   except subprocess.TimeoutExpired:proc.kill();proc.communicate()
  try:
   (OUT/(case['name']+'.log')).write_text(logs(name));r.setdefault('events',events(name))
   docker('rm','-f',name)
  except Exception as exc:r['cleanup_error']=repr(exc)
  (OUT/(case['name']+'.json')).write_text(json.dumps(r,indent=2))
 return r

image=info(IMAGE)
assert image['Config']['Labels']['org.opencontainers.image.revision']=='288223a2acb62bd6893e3370268f854bb2e16b12'
assert image['Config']['Entrypoint'] is None
cases=[{'name':'grace120-long-'+str(i),'durations':[47],'shutdown_window':120} for i in range(3)]
cases += [{'name':'grace120-multi','durations':[47,47,47],'shutdown_window':120},
 {'name':'grace120-active-term','durations':[47,47,47],'shutdown_window':120,'early':True},
 {'name':'observer-grace120','durations':[47],'shutdown_window':120,'observer':True},
 {'name':'observer-forced30','durations':[47],'force':True,'observer':True}]
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(trial,cases))
summary={'image_id':IMAGE,'passed':all(x['passed'] for x in results),'cases':[{'name':x['case']['name'],'passed':x['passed'],'exit':x.get('exit'),'error':x.get('error'),'diagnostic_log_tail':x.get('diagnostic_log_tail'),'term_sent_wall':x.get('term_sent_wall'),'exit_observed_wall':x.get('exit_observed_wall'),'events':[e for e in x.get('events',[]) if e['event']!='executor_activity']} for x in results]}
(OUT/'summary.json').write_text(json.dumps(summary,indent=2));print('RETIREMENT_RESULTS '+json.dumps(summary),flush=True)
assert summary['passed']
