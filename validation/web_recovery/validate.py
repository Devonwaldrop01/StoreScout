"""No production secrets, service APIs or database access."""
import concurrent.futures,json,os,pathlib,subprocess,time
ROOT=pathlib.Path(__file__).resolve().parent
OUT=pathlib.Path(os.environ['RUNNER_TEMP'])/'recovery-evidence'
SHA='288223a2acb62bd6893e3370268f854bb2e16b12'
names=[];results={'sha':SHA,'passed':False}
def run(*args,timeout=120):
 p=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
 if p.returncode:raise RuntimeError((args[:4],p.returncode,p.stdout[-2000:],p.stderr[-2000:]))
 return p.stdout.strip()
def docker(*args,**kw):return run('docker',*args,**kw)
def info(n):return json.loads(docker('inspect',n))[0]
def logs(n):
 p=subprocess.run(['docker','logs',n],capture_output=True,text=True)
 return p.stdout+p.stderr
def waitfor(f,seconds=30):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  if f():return
  time.sleep(.2)
 raise AssertionError('readiness timeout')
try:
 image=info('storescout-recovery:test')
 assert image['Os']=='linux' and image['Architecture']=='amd64'
 assert image['Config']['Entrypoint'] is None
 assert image['Config']['Labels']['org.opencontainers.image.revision']==SHA
 results['image_id']=image['Id'];results['image_config']=image['Config']
 packages=json.loads(docker('run','--rm','--network','none',image['Id'],'python','-c','import importlib.metadata as m,json;print(json.dumps({d.metadata["Name"]:d.version for d in m.distributions()}))'))
 (OUT/'packages.json').write_text(json.dumps(packages,indent=2))
 p=subprocess.run(['docker','run','--rm','--network','none',image['Id'],'python','-m','pip','check'],capture_output=True,text=True)
 results['pip_check']={'exit':p.returncode,'output':p.stdout+p.stderr}
 assert p.returncode==0,results['pip_check']
 for index,sig in enumerate(('SIGTERM','SIGINT')):
  name='recovery-web-'+str(index);names.append(name)
  command=['uvicorn','app.main:app','--host','0.0.0.0','--port','10000']
  docker('run','-d','--name',name,'--network','none','--read-only',
   '-e','PORT=10000','-e','PYTHONDONTWRITEBYTECODE=1','-e','PYTHONPATH=/validation',
   '-e','SUPABASE_URL=http://127.0.0.1:19991','-e','SUPABASE_SERVICE_ROLE_KEY=synthetic-only',
   '-e','REDIS_URL=rediss://127.0.0.1:19992/0?ssl_cert_reqs=required&ssl_check_hostname=true',
   '-e','STORE_INDEX_DEPLOYMENT_HOLD=true','-e','STORE_INDEX_CANARY_ENABLED=false',
   '-v',str(ROOT/'sitecustomize.py')+':/validation/sitecustomize.py:ro',image['Id'],*command)
  waitfor(lambda:'Application startup complete' in logs(name))
  assert info(name)['Path']=='uvicorn' and info(name)['Args']==command[1:]
  proof=json.loads(docker('exec',name,'python','-ISB','-c',
   'import pathlib,json;p=pathlib.Path("/proc/1");s=dict(x.split(":",1) for x in (p/"status").read_text().splitlines());print(json.dumps({"argv":(p/"cmdline").read_bytes().decode().split(chr(0))[:-1],"ppid":s["PPid"].strip(),"tcp":(p/"net/tcp").read_text()}))'))
  assert proof['ppid']=='0' and 'uvicorn' in proof['argv'][1],proof
  assert '00000000:2710' in proof['tcp']
  assert len(docker('top',name,'-eo','pid,ppid,comm').splitlines())==2
  probe='import http.client;c=http.client.HTTPConnection("127.0.0.1",10000,timeout=5);c.request("GET","/");r=c.getresponse();assert r.status==200;r.read();c.close();print("HTTP200")'
  begun=time.monotonic()
  for _ in range(12 if index==0 else 1):
   assert docker('exec',name,'python','-ISB','-c',probe)=='HTTP200'
   assert info(name)['State']['Running'] and info(name)['RestartCount']==0
   time.sleep(5 if index==0 else .1)
  # Observe effective client configuration only; do not connect to Redis.
  tls=json.loads(docker('exec',name,'python','-B','-c',
   'import json,redis,os;from app.tasks.celery_app import celery;b=celery.connection_for_write();r=redis.from_url(os.environ["REDIS_URL"]);c=r.connection_pool.connection_class(**r.connection_pool.connection_kwargs);print(json.dumps({"broker":b.ssl,"cert":int(c.cert_reqs),"hostname":c.check_hostname}))').splitlines()[0])
  assert tls['broker']['ssl_cert_reqs']==2 and tls['broker']['ssl_check_hostname'] is True
  assert tls['cert']==2 and tls['hostname'] is True
  seconds=round(time.monotonic()-begun,2)
  docker('kill','--signal',sig,name);exitcode=int(docker('wait',name,timeout=15))
  output=logs(name)
  assert exitcode==0 and 'Application shutdown complete' in output and 'Finished server process' in output
  assert 'OFFLINE_AUDIT {"events": []}' in output,output
  assert not any(x in output for x in ('beat: Starting','mingle:','Task received','Warm shutdown'))
  results.setdefault('cases',[]).append({'signal':sig,'exit':exitcode,'seconds':seconds,'restart_count':0,'proof':proof,'tls':tls,'outbound_events':0})
 results['passed']=True
finally:
 for name in names:
  try:
   (OUT/(name+'.log')).write_text(logs(name))
   (OUT/(name+'.json')).write_text(json.dumps(info(name),indent=2))
   docker('rm','-f',name)
  except Exception as e:print(type(e).__name__)
 (OUT/'results.json').write_text(json.dumps(results,indent=2))
 print('RECOVERY_RESULTS '+json.dumps(results),flush=True)

