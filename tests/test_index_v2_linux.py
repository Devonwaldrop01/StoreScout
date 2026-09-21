"""Linux-only guards; run in the candidate image with network disabled."""
import json,os,signal,subprocess,sys,time
from pathlib import Path
import pytest

pytestmark=pytest.mark.skipif(sys.platform!='linux',reason='Requires candidate Linux image')


def test_child_limits_and_parent_death_guard():
    child_code="from index_v2.child import limits; limits(); import ctypes,json,os,resource,signal; p=ctypes.c_int(); ctypes.CDLL(None).prctl(2,ctypes.byref(p)); print(json.dumps({'pid':os.getpid(),'parent_death_signal':p.value,'address_space':resource.getrlimit(resource.RLIMIT_AS),'cpu':resource.getrlimit(resource.RLIMIT_CPU),'file_size':resource.getrlimit(resource.RLIMIT_FSIZE)}),flush=True); signal.pause()"
    # The intermediate parent is deliberately killed in this isolated test only.
    parent_code="import subprocess,sys,time; from index_v2.worker import child_environment; subprocess.Popen([sys.executable,'-c',"+repr(child_code)+"],env=child_environment()); time.sleep(120)"
    parent=subprocess.Popen([sys.executable,'-c',parent_code],stdout=subprocess.PIPE,text=True)
    pid=None
    try:
        import select
        assert select.select([parent.stdout],[],[],10)[0], 'Child failed to initialize'
        data=json.loads(parent.stdout.readline());pid=data['pid']
        assert data['parent_death_signal']==signal.SIGKILL
        assert data['address_space']==[320*1024*1024]*2
        assert data['cpu']==[60,60] and data['file_size']==[2*1024*1024]*2
        parent.kill();parent.wait(timeout=5)
        for _ in range(50):
            path=Path(f'/proc/{pid}/stat')
            if not path.exists() or path.read_text().split(') ')[1].split()[0]=='Z': break
            time.sleep(.1)
        else: pytest.fail('Child remained executable after supervisor death')
    finally:
        if parent.poll() is None: parent.kill();parent.wait(timeout=5)
        if pid:
            try: os.kill(pid,signal.SIGKILL)
            except ProcessLookupError: pass


@pytest.mark.parametrize('sig',[signal.SIGTERM,signal.SIGINT])
def test_disabled_direct_entrypoint_clean_exit(sig,tmp_path):
    from index_v2.worker import child_environment,ROOT
    env=child_environment();env['INDEX_V2_ENABLED']='false'
    p=subprocess.Popen([str(ROOT/'scripts/store_index_v2.py')],cwd=tmp_path,env=env,stdout=subprocess.PIPE,text=True)
    try:
        import select
        assert select.select([p.stdout],[],[],10)[0]
        assert 'disabled; no jobs or application initialized' in p.stdout.readline()
        cmdline=Path(f'/proc/{p.pid}/cmdline').read_bytes().split(b'\0')
        assert b'python' in cmdline[0] and b'-c' not in cmdline
        assert p.poll() is None and not list(tmp_path.iterdir())
        p.send_signal(sig);assert p.wait(timeout=5)==0
    finally:
        if p.poll() is None: p.kill();p.wait(timeout=5)


def test_real_classifier_with_non_pid1_supervisor():
    code="from index_v2.worker import execute_child; from test_index_v2 import catalog; import os; assert os.getpid()!=1; assert execute_child({'stage':'classify','row':catalog()},lambda:None,lambda:False)['eligible']"
    env=dict(os.environ, PYTHONPATH=os.pathsep.join([str(Path.cwd()),str(Path.cwd()/'tests'),os.environ.get('PYTHONPATH','')]))
    result=subprocess.run([sys.executable,'-c',code],env=env,capture_output=True,text=True,timeout=20)
    assert result.returncode==0, result.stderr


@pytest.mark.parametrize('expected',['', '0', '99999999'])
def test_missing_or_mismatched_supervisor_rejected(expected):
    from index_v2.worker import child_environment
    env=child_environment()
    if expected: env['INDEX_V2_SUPERVISOR_PID']=expected
    else: env.pop('INDEX_V2_SUPERVISOR_PID')
    result=subprocess.run([sys.executable,'-c','from index_v2.child import limits; limits()'],env=env,capture_output=True,text=True,timeout=10)
    assert result.returncode==1 and 'Expected supervisor absent' in result.stderr


def test_parent_change_during_guard_installation_rejected(monkeypatch):
    import ctypes
    from index_v2.child import limits
    monkeypatch.setenv('INDEX_V2_SUPERVISOR_PID','123')
    parents=iter([123,1]);monkeypatch.setattr(os,'getppid',lambda:next(parents))
    class Guard:
        def prctl(self,*args): return 0
    monkeypatch.setattr(ctypes,'CDLL',lambda *args:Guard())
    with pytest.raises(RuntimeError,match='Supervisor absent'): limits()


def test_parent_vanished_before_guard_installation(tmp_path):
    gate=tmp_path/'release';result=tmp_path/'result'
    child_code=f"""
import os,time
from pathlib import Path
from index_v2.child import limits
gate=Path({str(gate)!r});result=Path({str(result)!r})
while not gate.exists(): time.sleep(.01)
try: limits()
except RuntimeError as exc: result.write_text(str(exc))
else: result.write_text('UNSAFE accepted orphan')
"""
    parent_code="import subprocess,sys,time; from index_v2.worker import child_environment; p=subprocess.Popen([sys.executable,'-c',"+repr(child_code)+"],env=child_environment(),stdout=subprocess.DEVNULL); print(p.pid,flush=True); time.sleep(120)"
    parent=subprocess.Popen([sys.executable,'-c',parent_code],stdout=subprocess.PIPE,text=True)
    pid=None
    try:
        import select
        assert select.select([parent.stdout],[],[],10)[0]
        pid=int(parent.stdout.readline());parent.kill();parent.wait(timeout=5)
        gate.touch()
        for _ in range(100):
            if result.exists(): break
            time.sleep(.05)
        assert result.read_text()=='Expected supervisor absent'
    finally:
        if parent.poll() is None: parent.kill();parent.wait(timeout=5)
        if pid:
            try: os.kill(pid,signal.SIGKILL)
            except ProcessLookupError: pass
