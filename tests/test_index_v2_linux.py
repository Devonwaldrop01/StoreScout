"""Linux-only guards; run in the candidate image with network disabled."""
import json,os,signal,subprocess,sys,time
from pathlib import Path
import pytest

pytestmark=pytest.mark.skipif(sys.platform!='linux',reason='Requires candidate Linux image')


def test_child_limits_and_parent_death_guard():
    child_code="from index_v2.child import limits; limits(); import ctypes,json,os,resource,signal; p=ctypes.c_int(); ctypes.CDLL(None).prctl(2,ctypes.byref(p)); print(json.dumps({'pid':os.getpid(),'parent_death_signal':p.value,'address_space':resource.getrlimit(resource.RLIMIT_AS),'cpu':resource.getrlimit(resource.RLIMIT_CPU),'file_size':resource.getrlimit(resource.RLIMIT_FSIZE)}),flush=True); signal.pause()"
    # The intermediate parent is deliberately killed in this isolated test only.
    parent_code="import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',"+repr(child_code)+"]); time.sleep(120)"
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
