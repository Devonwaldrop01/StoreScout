"""Host-side isolated permission/exit evidence checks. No production access."""
import concurrent.futures, json, os, pathlib, subprocess, time, traceback
ROOT=pathlib.Path(__file__).resolve().parent
OUT=pathlib.Path(os.environ['RUNNER_TEMP'])/'retirement-evidence'
IMAGE='sha256:bd54189c67f7ce0154b0c1ca8bd21b2f57f4bab0f18eb5e8e55b995ea155f0c9'
def run(*args,timeout=40,check=True):
    p=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
    if check and p.returncode:raise RuntimeError((args[:3],p.returncode,p.stderr[-500:]))
    return p
def docker(*args,**kwargs):return run('docker',*args,**kwargs)
def state(name):return json.loads(docker('inspect',name).stdout)[0]['State']
def truth(name):
    return [json.loads(s) for s in docker('logs',name).stdout.splitlines() if s.startswith('{')]
def waitfor(predicate,seconds=10):
    until=time.monotonic()+seconds
    while time.monotonic()<until:
        if predicate():return
        time.sleep(.1)
    raise AssertionError('fixture condition timeout')
def trial(mode):
    name='observer-feasibility-'+mode
    result={'case':mode,'passed':False};observer=None;stream=None
    try:
        docker('run','-d','--name',name,'--network','none','--read-only',
               '-v',str(ROOT)+':/validation:ro',IMAGE,'python','-IB',
               '/validation/observer_target.py',mode)
        waitfor(lambda:any(e['event']=='ready' for e in truth(name)))
        host_pid=state(name)['Pid']; result['host_pid']=host_pid
        if mode=='permission':
            p=docker('exec',name,'python','-IB','/validation/exit_observer.py','1',check=False,timeout=5)
            result['sibling_probe_exit']=p.returncode
            result['sibling_probe_output']=p.stdout
            # CI default-container policy, NOT an assertion about Render policy.
            assert p.returncode==2 and 'attachment_unavailable' in p.stdout
            result['passed']=True
            return result
        observer_path=OUT/(mode+'-kernel-observer.jsonl')
        stream=observer_path.open('w')
        observer=subprocess.Popen(['sudo','python3','-IB',str(ROOT/'exit_observer.py'),str(host_pid)],stdout=stream,stderr=subprocess.STDOUT)
        waitfor(lambda:'"event": "attached"' in observer_path.read_text(),5)
        result['predates_attachment']=any(e['event']=='active' for e in truth(name))
        assert result['predates_attachment']
        if mode=='observer_loss':
            observer.terminate();observer.wait(timeout=5)
            assert state(name)['Running']
            # Exit evidence is incomplete. Absence of EXITKILL must leave target alive.
            result['target_survived_observer_loss']=True
        docker('kill','--signal','SIGTERM',name)
        if mode=='forced':
            docker('kill','--signal','SIGKILL',name)
        result['exit']=int(docker('wait',name,timeout=25).stdout)
        if observer.poll() is None:observer.wait(timeout=5)
        stream.close();stream=None
        result['observer']=[json.loads(s) for s in observer_path.read_text().splitlines()]
        result['truth']=truth(name)
        terminal=[e for e in result['observer'] if e['event']=='terminal']
        completed=[e for e in result['truth'] if e['event']=='fully_finished']
        if mode=='normal':
            assert result['exit']==0 and len(completed)==3 and terminal[0]['exit_code']==0
            assert max(e['wall'] for e in completed)<terminal[0]['wall']
        elif mode=='abrupt_zero':
            assert result['exit']==0 and not completed and terminal[0]['exit_code']==0
            result['zero_exit_is_not_semantic_completion']=True
        elif mode=='forced':
            assert result['exit']==137 and not completed and terminal[0]['signal']==9
        elif mode=='observer_loss':
            assert result['exit']==0 and not terminal
        assert all(e['event'] in ('attached','signal_delivery','pre_exit','terminal') for e in result['observer'])
        result['passed']=True
    except Exception:
        result['error']=traceback.format_exc()
    finally:
        if observer and observer.poll() is None:
            observer.terminate();observer.wait(timeout=5)
        if stream:stream.close()
        docker('rm','-f',name,check=False)
        OUT.joinpath(mode+'-feasibility.json').write_text(json.dumps(result,indent=2))
    return result
OUT.mkdir(exist_ok=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
    results=list(pool.map(trial,['permission','normal','abrupt_zero','forced','observer_loss']))
summary=dict(passed=all(x['passed'] for x in results),image_id=IMAGE,cases=results,
             production_ready=False)
OUT.joinpath('observer-feasibility.json').write_text(json.dumps(summary,indent=2))
print('OBSERVER_FEASIBILITY '+json.dumps(summary),flush=True)
assert summary['passed']
