"""Brokerless supervisor: bounded children, durable leases, no legacy clients."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
from .store import LostLease

ROOT=Path(__file__).resolve().parents[1]
SECRET_NAMES=('SUPABASE_SERVICE_ROLE_KEY','SUPABASE_SECRET_KEY','DATABASE_URL','REDIS_URL',
              'ANTHROPIC_API_KEY','INTERNAL_SECRET','STRIPE_SECRET_KEY','RESEND_API_KEY',
              'CELERY_BROKER_URL','CELERY_RESULT_BACKEND','SUPABASE_KEY','SUPABASE_ANON_KEY')


def assert_isolated_env(env=None):
    env=os.environ if env is None else env
    present=[name for name in SECRET_NAMES if env.get(name)]
    if present: raise ValueError('V2 refuses inherited legacy credentials: '+','.join(present))


def child_environment():
    result={k:os.environ[k] for k in ('PATH','SYSTEMROOT','WINDIR','TEMP','TMP','LANG') if k in os.environ}
    result.update(PYTHONPATH=str(ROOT),PYTHONUNBUFFERED='1',PYTHONUTF8='1',STORE_INDEX_DEPLOYMENT_HOLD='true')
    result['INDEX_V2_SUPERVISOR_PID']=str(os.getpid())
    return result


def memory_bytes():
    for filename in ('/sys/fs/cgroup/memory.current','/sys/fs/cgroup/memory/memory.usage_in_bytes'):
        try: return int(Path(filename).read_text())
        except (OSError,ValueError): pass
    if sys.platform=='linux': raise RuntimeError('Container memory accounting unavailable')
    return 0  # local Windows validation only; production entrypoint requires Linux


def terminate(child):
    """Reap the child and prove its process group gone before another dispatch."""
    try:
        if os.name=='posix':
            try: os.killpg(child.pid,signal.SIGTERM)
            except ProcessLookupError: pass
        elif child.poll() is None: child.terminate()
        try: child.wait(timeout=3)
        except subprocess.TimeoutExpired:
            if os.name=='posix': os.killpg(child.pid,signal.SIGKILL)
            else: child.kill()
            child.wait(timeout=3)
        if os.name=='posix':
            try: os.killpg(child.pid,0)
            except ProcessLookupError: return
            # A descendant survived its leader: do not dispatch anything else.
            os.killpg(child.pid,signal.SIGKILL)
            raise ChildFailed('child_termination_unconfirmed')
        if child.poll() is None: raise ChildFailed('child_termination_unconfirmed')
    except (OSError,subprocess.TimeoutExpired) as exc:
        raise ChildFailed('child_termination_unconfirmed') from exc


class ChildFailed(RuntimeError):
    def __init__(self,reason):
        self.reason=reason;self.termination_confirmed=False;super().__init__(reason)


def execute_child(payload,renew,stop):
    """No DB path passed to child. Lease loss kills it before further dispatch."""
    with tempfile.TemporaryDirectory(prefix='storescout-v2-') as folder:
        output=Path(folder)/'result.json'
        raw=json.dumps(payload).encode()
        if len(raw)>2*1024*1024: raise ChildFailed('invalid_child_input')
        # A regular input file avoids a blocked stdin pipe before supervision starts.
        # It contains only public catalog fields and is removed with the temp directory.
        input_path=Path(folder)/'input.json';input_path.write_bytes(raw)
        journal_path=Path(folder)/'protection.json';last_evidence=None
        env=child_environment();env['INDEX_V2_PROTECTION_JOURNAL']=str(journal_path)
        def collect():
            nonlocal last_evidence
            if journal_path.exists():
                if journal_path.stat().st_size>8192: raise ChildFailed('invalid_child_result')
                from .protection import validated
                evidence=validated(json.loads(journal_path.read_text(encoding='utf8')))
                if evidence!=last_evidence:
                    if hasattr(renew,'protection'): renew.protection(evidence)
                    last_evidence=evidence
        with output.open('wb') as stream, input_path.open('rb') as input_stream:
            child=subprocess.Popen([sys.executable,'-m','index_v2.child'],stdin=input_stream,
                stdout=stream,stderr=subprocess.DEVNULL,cwd=folder,env=env,
                start_new_session=(os.name=='posix'))
            failure=None
            try:
                start=last_renew=time.monotonic()
                while child.poll() is None:
                    collect()
                    if stop(): raise ChildFailed('interrupted_shutdown')
                    if time.monotonic()-start>=90: raise ChildFailed('child_timeout')
                    if memory_bytes()>=400*1024*1024: raise ChildFailed('memory_ceiling')
                    if output.stat().st_size>2*1024*1024: raise ChildFailed('invalid_child_result')
                    if time.monotonic()-last_renew>=20:
                        renew();last_renew=time.monotonic()
                    time.sleep(.1)
                if (sys.platform=='linux' and child.returncode==-signal.SIGALRM
                        and time.monotonic()-start>=90):
                    raise ChildFailed('child_timeout')
                if child.returncode!=0: raise ChildFailed('child_exit_'+str(child.returncode))
            except ChildFailed as exc:
                failure=exc
                raise
            finally:
                terminate(child)
                if failure is not None: failure.termination_confirmed=True
                collect()
        renew()
        if output.stat().st_size>2*1024*1024: raise ChildFailed('invalid_child_result')
        try:
            result=json.loads(output.read_text(encoding='utf8'))
            if not isinstance(result,dict): raise ValueError()
            result['supervisor_seconds']=time.monotonic()-start
            return result
        except (ValueError,OSError): raise ChildFailed('invalid_child_result')


def process_job(store,job,executor=execute_child,stop=lambda:False):
    from .compute import retry_time
    from app.services.discovery_quality import is_recent_verified,is_classification_usable
    renew=lambda:store.renew(job)
    renew.protection=lambda events:store.record_protection(job,events)
    stage='verify'
    try:
        if job['state']=='verified': row=json.loads(job['row_json'])
        else:
            store.transition(job,'verifying')
            result=executor({'stage':'verify','canonical':job['canonical'],'fetch_host':job['fetch_host']},renew,stop)
            if result.get('protection_events'): store.record_protection(job,result['protection_events'])
            result=store.with_protection(job,result,result.get('state')=='verified_shopify')
            row=result.get('row')
            if result.get('state')!='verified_shopify':
                state=result.get('state') or 'temporarily_unreachable'
                store.complete(job,reason=state,retry_at=retry_time(job,state,result.get('retry_after_at')),result=result)
                return
            if not row or row.get('domain')!=job['canonical'] or not is_recent_verified(row):
                raise ChildFailed('invalid_child_result')
            store.verified(job,row,result)
            if store.canary_stopped():
                store.hold_verified(job)
                return
        stage='classify'
        store.transition(job,'classifying')
        result=executor({'stage':'classify','row':row},renew,stop)
        updated=result['row']
        if updated.get('domain')!=job['canonical'] or updated.get('catalog_observation',{}).get('signature')!=row['catalog_observation']['signature']:
            raise ChildFailed('invalid_child_result')
        eligible=is_recent_verified(updated) and is_classification_usable(updated) and (updated.get('category_confidence') or 0)>=55
        store.complete(job,row=updated,eligible=eligible,reason=None if eligible else result.get('reason') or 'classification_excluded',
            classification_metrics={k:result[k] for k in ('supervisor_seconds','peak_rss_kib') if k in result})
    except LostLease:
        store.pause(job['batch'],'lease_lost');raise
    except Exception as exc:
        reason=exc.reason if isinstance(exc,ChildFailed) else 'invalid_child_result'
        if reason=='child_timeout' and exc.termination_confirmed and stage=='verify':
            try:
                store.complete(job,reason='child_timeout',
                    retry_at=retry_time(job,'temporarily_unreachable'),
                    result={'state':'temporarily_unreachable','failure':'child_timeout',
                            'request_accounting':'unknown','termination_confirmed':True})
                return
            except Exception:
                store.pause(job['batch'],'timeout_persistence_failed')
                raise
        # Preserve a completed verification checkpoint for classification retry.
        # Leave ownership until expiry; never relabel an unknown child as success.
        store.pause(job['batch'],reason)
        store.event(job['attempt_id'],'supervisor_stopped_'+reason)
        raise


def run(store,batch,stop):
    import shutil
    assert_isolated_env()
    if os.environ.get('INDEX_V2_ENABLED')!='true' or os.environ.get('INDEX_V2_MANIFEST_SHA256')!=batch:
        raise ValueError('V2 execution not separately authorized')
    manifest=store.manifest(batch)
    while not stop():
        if memory_bytes()>=400*1024*1024:
            store.pause(batch,'memory_ceiling');return
        if shutil.disk_usage(store.path.parent).free<512*1024*1024:
            store.pause(batch,'disk_headroom');return
        try: job=store.claim(batch)
        except ValueError:
            if not store.canary: raise
            store.pause(batch,'canary_accounting_review_required');return
        if job:
            process_job(store,job,stop=stop)
            print(json.dumps(store.summary()),flush=True)
        else: time.sleep(1)
