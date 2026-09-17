"""OFFLINE prototype: observe an existing Linux PID; never launch/wrap the app.

Requires ptrace permission. Seizing does not stop the target; signal-delivery
and exit stops are promptly continued. No EXITKILL option is used. This is
intrusive kernel tracing, not approved or installed in production.
"""
import ctypes
import json
import os
import pathlib
import signal
import sys
import time

pid = int(sys.argv[1])
libc = ctypes.CDLL(None, use_errno=True)
libc.ptrace.restype = ctypes.c_long

def emit(event, **fields):
    print(json.dumps(dict(event=event, wall=time.time(), pid=pid, **fields)), flush=True)

def trace(request, data=0):
    ctypes.set_errno(0)
    result = libc.ptrace(request, pid, ctypes.c_void_p(0), data)
    if result == -1:
        err = ctypes.get_errno()
        raise OSError(err, os.strerror(err))
    return result

try:
    # stat starttime disambiguates PID reuse; do not read environment or arguments.
    start_ticks = pathlib.Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[19]
    trace(0x4206, 0x40)  # PTRACE_SEIZE, PTRACE_O_TRACEEXIT only
except OSError as exc:
    emit('attachment_unavailable', errno=exc.errno)
    sys.exit(2)

emit('attached', start_ticks=start_ticks)
while True:
    waited, status = os.waitpid(pid, 0x40000000)  # __WALL
    if os.WIFEXITED(status) or os.WIFSIGNALED(status):
        emit('terminal', raw_status=status,
             exit_code=os.WEXITSTATUS(status) if os.WIFEXITED(status) else None,
             signal=os.WTERMSIG(status) if os.WIFSIGNALED(status) else None)
        break
    if not os.WIFSTOPPED(status):
        raise RuntimeError('unexpected wait status')
    if status >> 16 == 6:  # PTRACE_EVENT_EXIT is PRE-exit, not final proof
        message = ctypes.c_ulong()
        trace(0x4201, ctypes.byref(message))
        emit('pre_exit', raw_status=message.value)
        trace(7)
    else:
        delivered = os.WSTOPSIG(status)
        emit('signal_delivery', signal=delivered)
        trace(7, delivered)  # Preserve the application's signal handling.
