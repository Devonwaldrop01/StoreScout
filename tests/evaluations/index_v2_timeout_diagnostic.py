"""Diagnostic overlay only: run the unchanged retained-image child/supervisor.

Only public 5to9vibe.com verification is permitted. No database is opened.
No response bodies, headers, credentials or environment values are logged.
"""
import datetime
import faulthandler
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time

START = time.monotonic()


def log(event, **values):
    print(json.dumps(dict(event=event, elapsed=round(time.monotonic()-START, 6),
                         utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), **values)),
          file=sys.stderr, flush=True)


def child():
    faulthandler.enable()
    faulthandler.dump_traceback_later(80, repeat=False)
    from index_v2.worker import assert_isolated_env
    assert_isolated_env()
    from curl_cffi import Curl, CurlInfo
    from curl_cffi.requests import Session
    import app.services.store_index as probe
    from index_v2 import child as original

    dns = socket.getaddrinfo
    def resolve(host, *args, **kwargs):
        log('dns_start', host=host)
        try:
            result = dns(host, *args, **kwargs)
            log('dns_end', addresses=len(result))
            return result
        except Exception as exc:
            log('dns_error', error=type(exc).__name__)
            raise
    socket.getaddrinfo = resolve

    perform = Curl.perform
    def timed_perform(self, *args, **kwargs):
        log('curl_start')
        try:
            return perform(self, *args, **kwargs)
        finally:
            timings = {}
            for name in ('NAMELOOKUP_TIME', 'CONNECT_TIME', 'APPCONNECT_TIME',
                         'STARTTRANSFER_TIME', 'TOTAL_TIME', 'REDIRECT_COUNT', 'RESPONSE_CODE'):
                try: timings[name] = self.getinfo(getattr(CurlInfo, name))
                except Exception: timings[name] = None
            log('curl_end', timings=timings)
    Curl.perform = timed_perform

    request = Session.request
    def timed_request(self, method, url, *args, **kwargs):
        log('request_start', method=method, url=url, timeout=kwargs.get('timeout'),
            allow_redirects=kwargs.get('allow_redirects'))
        try:
            response = request(self, method, url, *args, **kwargs)
            log('request_end', status=response.status_code)
            return response
        except Exception as exc:
            log('request_error', error=type(exc).__name__)
            raise
    Session.request = timed_request

    # Same regex objects, inputs and results; identify time spent inside each.
    class TimedPattern:
        def __init__(self, name, pattern): self.name, self.pattern = name, pattern
        def search(self, value, *args, **kwargs):
            log('regex_start', name=self.name, length=len(value))
            result = self.pattern.search(value, *args, **kwargs)
            log('regex_end', name=self.name)
            return result
        def finditer(self, value, *args, **kwargs):
            log('regex_start', name=self.name, length=len(value))
            yield from self.pattern.finditer(value, *args, **kwargs)
            log('regex_end', name=self.name)
    for name in ('_TITLE_RE', '_META_DESC_RE', '_META_DESC_RE2', '_OG_SITE_RE',
                 '_LANG_RE', '_MAILTO_RE', '_EMAIL_RE'):
        setattr(probe, name, TimedPattern(name, getattr(probe, name)))
    log('child_start', pid=os.getpid(), ppid=os.getppid(), python=sys.version)
    original.main()
    log('child_complete', forbidden_modules=[n for n in ('app.main', 'celery', 'redis',
        'supabase', 'anthropic') if n in sys.modules])


def parent(output):
    from index_v2 import worker
    worker.assert_isolated_env()
    output.mkdir(parents=True, exist_ok=False)
    original_popen, original_killpg = subprocess.Popen, getattr(os, 'killpg', None)
    children = []
    done = threading.Event()
    trace = (output/'child-stderr.txt').open('w', encoding='utf8')
    def launch(argv, **kwargs):
        assert argv == [sys.executable, '-m', 'index_v2.child']
        kwargs['stderr'] = trace
        actual = [sys.executable, str(Path(__file__).resolve()), '--child']
        log('child_launch', original_argv=argv, diagnostic_argv=actual,
            env_names=sorted(kwargs['env']), start_new_session=kwargs['start_new_session'])
        process = original_popen(actual, **kwargs)
        children.append(process)
        return process
    def killpg(pid, sig):
        log('signal_sent', process_group=pid, signal=int(sig))
        return original_killpg(pid, sig)
    subprocess.Popen = launch
    if original_killpg: os.killpg = killpg
    def sample():
        with (output/'process.jsonl').open('w', encoding='utf8') as stream:
            while not done.wait(5):
                rows = []
                for base in Path('/proc').glob('[0-9]*'):
                    try:
                        stat = (base/'stat').read_text()
                        # comm is constant Python; no argv/env/application payloads.
                        tail = stat[stat.rfind(')')+2:].split()
                        rows.append(dict(pid=int(base.name), state=tail[0], ppid=int(tail[1]),
                                         pgrp=int(tail[2]), utime=int(tail[11]), stime=int(tail[12])))
                    except OSError: pass
                stream.write(json.dumps(dict(elapsed=time.monotonic()-START, processes=rows))+'\n')
                stream.flush()
    monitor = threading.Thread(target=sample, daemon=True); monitor.start()
    result = {}
    try:
        data = worker.execute_child(dict(stage='verify', canonical='5to9vibe.com',
            fetch_host='5to9vibe.com'), lambda: log('lease_renew'), lambda: False)
        result = dict(outcome='returned', state=data.get('state'), requests=data.get('requests'),
                      supervisor_seconds=data.get('supervisor_seconds'))
    except Exception as exc:
        import traceback
        traceback.print_exc()
        result = dict(outcome='failed', exception=type(exc).__name__, reason=str(exc))
    finally:
        done.set(); monitor.join(6); trace.close()
        result.update(elapsed=time.monotonic()-START,
                      child_returncodes=[p.poll() for p in children],
                      child_dead=all(p.poll() is not None for p in children))
        (output/'result.json').write_text(json.dumps(result, indent=2), encoding='utf8')
        log('supervisor_finished', **result)


if __name__ == '__main__':
    if sys.argv[1:] == ['--child']: child()
    else: parent(Path(sys.argv[1]))
