"""Synthetic kernel-observer controls in the retained Python runtime.

Not application code. No network, credentials or business data. Phase records
are test ground truth and are deliberately unavailable to the exit observer.
"""
import concurrent.futures, json, os, signal, sys, threading, time
mode = sys.argv[1]
stop = threading.Event()
def emit(event, **fields):
    os.write(1,(json.dumps(dict(event=event,wall=time.time(),**fields))+'\n').encode())
def work(number):
    emit('active',operation=number)
    emit('waiting_network',operation=number)
    time.sleep(4)
    emit('external_effect_fixture',operation=number)
    time.sleep(.1)
    emit('persistence_ack_fixture',operation=number)
    emit('fully_finished',operation=number)
def term(signum,frame):
    emit('term_received',signal=signum)
    if mode == 'abrupt_zero':
        os._exit(0)
    stop.set()
signal.signal(signal.SIGTERM,term)
pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
futures=[pool.submit(work,i) for i in range(3)]
emit('ready', queued=2, active=1)
while not stop.wait(.1):
    pass
pool.shutdown(wait=True)
emit('joined_all')
