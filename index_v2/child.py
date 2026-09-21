"""One bounded child, no state writes. Input/output are public catalog JSON."""
import json
import os
import signal
import sys


def limits():
    if sys.platform=='linux':
        import ctypes,resource
        # If the supervisor dies, this child must not continue making requests.
        parent=int(os.environ.get('INDEX_V2_SUPERVISOR_PID','0'))
        if parent<1 or os.getppid()!=parent:
            raise RuntimeError('Expected supervisor absent')
        if ctypes.CDLL(None).prctl(1,signal.SIGKILL)!=0: raise RuntimeError('Parent-death guard unavailable')
        if os.getppid()!=parent: raise RuntimeError('Supervisor absent')
        resource.setrlimit(resource.RLIMIT_AS,(320*1024*1024,320*1024*1024))
        resource.setrlimit(resource.RLIMIT_CPU,(60,60))
        resource.setrlimit(resource.RLIMIT_FSIZE,(2*1024*1024,2*1024*1024))
        signal.alarm(90)


def main():
    limits()
    import importlib.abc
    class NoServiceClients(importlib.abc.MetaPathFinder):
        def find_spec(self,fullname,path=None,target=None):
            if fullname.split('.')[0] in {'redis','supabase','anthropic','celery','resend','stripe'} or any(
                fullname==prefix or fullname.startswith(prefix+'.') for prefix in ('app.main','app.tasks','app.api','app.core.database')):
                raise ImportError('Service clients and application startup are forbidden in V2 children')
    sys.meta_path.insert(0,NoServiceClients())
    payload=json.loads(sys.stdin.buffer.read(2*1024*1024))
    from .compute import classify,verified_row
    if payload['stage']=='classify': result=classify(payload['row'])
    else:
        from .transport import Transport
        from app.services.store_index import probe_store_catalog
        from app.services.verification_lifecycle import classify_probe
        transport=Transport(payload['fetch_host'])
        try:
            probe=probe_store_catalog(payload['fetch_host'],make_client=lambda:transport,
                get_response=transport.get,pace=transport.pace)
        except Exception:
            probe={'reachable':False,'access_state':transport.stop_state or 'temporarily_unreachable'}
        if not probe.get('monitorable') and transport.stop_state:
            probe['access_state']=transport.stop_state
        result={'state':classify_probe(probe,60),'row':verified_row(payload['canonical'],probe),
                'retry_after_at':probe.get('retry_after_at'),'requests':transport.requests}
    if sys.platform=='linux':
        import resource
        result['peak_rss_kib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # No imports with side effects are needed by either compute path.
    if any(n in sys.modules for n in ('app.main','app.tasks.celery_app','app.core.database')):
        raise RuntimeError('Application lifecycle imported unexpectedly')
    sys.stdout.write(json.dumps(result,separators=(',',':')))


if __name__=='__main__': main()
