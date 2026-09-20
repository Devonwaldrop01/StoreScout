"""Mounted test harness only. Never copied into or used to change candidate code.

Capture the real execute_child call, changing only its discarded stderr sink.
Repeat as container PID1 and a normal child supervisor, with the same fixture,
limits, environment builder, cwd policy and exact candidate modules.
"""
import ast
from datetime import datetime, timezone
import hashlib
from importlib import metadata, util
import json
import os
from pathlib import Path
import platform
import re
import sqlite3
import subprocess
import sys
import tempfile
import traceback
from unittest.mock import patch

ROOT=Path('/app') if Path('/app/index_v2/worker.py').exists() else Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
ORIGINAL_POPEN=subprocess.Popen
PACKAGES=('pydantic','pydantic-settings','curl-cffi','fastapi','starlette','python-dotenv',
          'anthropic','httpx','supabase','redis','celery','cffi')
FILES=('index_v2/worker.py','index_v2/child.py','index_v2/compute.py',
       'app/services/store_index.py','app/services/store_dna.py','app/core/config.py')


def redact(text):
    # Fixture input is synthetic and child env is credential-free. Still redact
    # common credential-shaped assignments/authorization strings defensively.
    text=re.sub(r'(?i)(authorization\s*[:=]\s*)([^\r\n]+)',r'\1[REDACTED]',text)
    text=re.sub(r'(?i)((?:password|api_key|access_token|secret)\s*[=:]\s*)[^\s,}]+',r'\1[REDACTED]',text)
    return text


def save(path,value):
    path.write_text(json.dumps(value,indent=2),encoding='utf8')


def file_metadata():
    return {name:{'exists':(ROOT/name).is_file(),'readable':os.access(ROOT/name,os.R_OK),
        'sha256':hashlib.sha256((ROOT/name).read_bytes()).hexdigest() if (ROOT/name).is_file() else None}
        for name in FILES}


def snapshot():
    versions={}
    for name in PACKAGES:
        try: versions[name]=metadata.version(name)
        except metadata.PackageNotFoundError: versions[name]=None
    specs={}
    for name in ('index_v2','index_v2.child','app','app.services','pydantic','curl_cffi'):
        try:
            s=util.find_spec(name);specs[name]=None if s is None else {'origin':s.origin,'locations':list(s.submodule_search_locations or [])}
        except Exception as e: specs[name]={'error':type(e).__name__}
    return {'pid':os.getpid(),'ppid':os.getppid(),'python_executable':sys.executable,
        'python_realpath':str(Path(sys.executable).resolve()),'python_version':platform.python_version(),
        'platform':platform.platform(),'cwd':os.getcwd(),'sys_path':sys.path,'package_versions':versions,
        'module_specs':specs,'files':file_metadata(),
        'environment_presence':{name:bool(os.environ[name]) for name in sorted(os.environ)},
        'dot_env_exists':Path('.env').exists()}


def metadata_probe():
    result=snapshot()
    # Diagnostic-only fresh database, never any candidate or production DB.
    with tempfile.TemporaryDirectory(prefix='v2-permission-',dir=os.getcwd()) as folder:
        dbpath=Path(folder)/'permission.sqlite'
        db=sqlite3.connect(dbpath)
        try:
            mode=db.execute('PRAGMA journal_mode=WAL').fetchone()[0]
            db.execute('PRAGMA synchronous=FULL');db.execute('CREATE TABLE probe(value INTEGER)')
            db.execute('INSERT INTO probe VALUES (1)');db.commit()
        finally: db.close()
        db=sqlite3.connect(dbpath)
        try: persisted=db.execute('SELECT value FROM probe').fetchone()[0]==1
        finally: db.close()
        result['fresh_sqlite_probe']={'journal_mode':mode,'persisted_after_reopen':persisted}
    print(json.dumps(result))


def fixture():
    # Compile just the exact existing test fixture, avoiding pytest/test clients.
    from app.services.verification_lifecycle import successful_catalog
    from index_v2.compute import verified_row
    source=ast.parse((ROOT/'tests/test_index_v2.py').read_text())
    node=next(n for n in source.body if isinstance(n,ast.FunctionDef) and n.name=='catalog')
    ns={'NOW':datetime.now(timezone.utc),'successful_catalog':successful_catalog,'verified_row':verified_row}
    exec(compile(ast.Module(body=[node],type_ignores=[]),'candidate-catalog-fixture','exec'),ns)
    return {'stage':'classify','row':ns['catalog']()}


def attempt(directory,payload):
    from index_v2 import worker
    worker.assert_isolated_env()
    directory.mkdir(parents=True)
    record={'supervisor':snapshot(),'changes_to_child':'stderr capture only; argv, cwd, env, input and limits unchanged'}
    completed=[]
    stderr_path=directory/'child-stderr.txt'
    with stderr_path.open('wb') as diagnostic_stderr:
        class Capture(ORIGINAL_POPEN):
            def __init__(self,args,**kwargs):
                record['argv']=args
                record['cwd']=str(kwargs['cwd'])
                record['environment_presence']={k:bool(v) for k,v in sorted(kwargs['env'].items())}
                raw=Path(kwargs['stdin'].name).read_bytes()
                assert json.loads(raw)==payload
                record['input']={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'json_roundtrip':True,
                    'keys':sorted(payload),'synthetic_fixture':True}
                # Same executable, cwd and environment as the real child; this
                # metadata process runs to completion before the real launch.
                with (directory/'child-context.json').open('wb') as metadata_out:
                    probe=ORIGINAL_POPEN([args[0],str(Path(__file__).resolve()),'metadata'],
                        cwd=kwargs['cwd'],env=kwargs['env'],stdout=metadata_out,stderr=subprocess.PIPE)
                    _,err=probe.communicate(timeout=20)
                    record['context_probe']={'exit_code':probe.returncode,'stderr':redact(err.decode(errors='replace'))}
                self.output_path=Path(kwargs['stdout'].name)
                self.captured=False
                kwargs['stderr']=diagnostic_stderr
                super().__init__(args,**kwargs)
                record['child_pid']=self.pid
            def capture_exit(self,code):
                if code is not None and not self.captured:
                    self.captured=True;record['exit_code']=code
                    (directory/'child-stdout.txt').write_text(redact(self.output_path.read_text(errors='replace')),encoding='utf8')
                    completed.append(code)
                return code
            def poll(self): return self.capture_exit(super().poll())
            def wait(self,timeout=None): return self.capture_exit(super().wait(timeout=timeout))
        try:
            with patch.object(worker.subprocess,'Popen',Capture):
                value=worker.execute_child(payload,lambda:None,lambda:False)
            record['result']={'eligible':value.get('eligible'),'confidence':value.get('row',{}).get('category_confidence')}
        except Exception as exc:
            record['exception']=type(exc).__name__+': '+str(exc)
            (directory/'supervisor-traceback.txt').write_text(redact(traceback.format_exc()),encoding='utf8')
    stderr=redact(stderr_path.read_text(errors='replace'))
    stderr_path.write_text(stderr,encoding='utf8')
    record['stderr_sha256']=hashlib.sha256(stderr.encode()).hexdigest()
    save(directory/'attempt.json',record)
    print(json.dumps({'attempt':directory.name,'supervisor_pid':record['supervisor']['pid'],
        'exit_code':record.get('exit_code'),'exception':record.get('exception'),'stderr':stderr,
        'result':record.get('result')}),flush=True)
    return record


def main():
    if len(sys.argv)>1 and sys.argv[1]=='metadata': metadata_probe();return
    nested=len(sys.argv)>1 and sys.argv[1]=='nested'
    out=Path(sys.argv[2] if nested else sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=True)
    from index_v2.worker import assert_isolated_env
    assert_isolated_env()
    payload_path=out/'synthetic-input.json'
    payload=json.loads(payload_path.read_text()) if payload_path.exists() else fixture()
    if not payload_path.exists(): save(payload_path,payload)
    if nested:
        results=[attempt(out/f'non-pid1-{i}',payload) for i in (1,2)]
        save(out/'non-pid1-results.json',results);return
    if sys.platform=='linux': assert os.getpid()==1, 'Exact failing container parent layout required'
    results=[attempt(out/f'pid1-{i}',payload) for i in (1,2)]
    save(out/'pid1-results.json',results)
    # Isolate the suspected PID1 condition without changing candidate code,
    # child argv, environment builder, guards, budgets, or fixture bytes.
    with (out/'non-pid1-driver.log').open('wb') as log:
        p=ORIGINAL_POPEN([sys.executable,str(Path(__file__).resolve()),'nested',str(out)],
            stdout=log,stderr=log,start_new_session=(os.name=='posix'))
        try: code=p.wait(timeout=240)
        except subprocess.TimeoutExpired: p.kill();p.wait();raise
    save(out/'driver-result.json',{'non_pid1_driver_exit':code,'candidate_code_modified':False,
        'comparison':'same execute_child and synthetic JSON; container PID1 versus child supervisor',
        'environment_values_reported':False})
    assert code==0, 'Diagnostic helper failed; inspect retained log'


if __name__=='__main__': main()
