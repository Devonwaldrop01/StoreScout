"""Test-only audit hook; no application changes."""
import atexit,json,sys
events=[]
def audit(event,args):
    if event in ('socket.connect','subprocess.Popen','os.system'):
        events.append(event)
        raise RuntimeError('OFFLINE_AUDIT forbids outbound connections/processes')
sys.addaudithook(audit)
atexit.register(lambda:print('OFFLINE_AUDIT '+json.dumps({'events':events}),flush=True))

