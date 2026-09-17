"""Isolated real-route/Redis TLS counterexample to a fixed legacy drain wait.

No production secrets or access. Merchant responses and DB are in-memory
fixtures; Redis-py, TLS, ASGI routing, AnyIO and legacy verification code are real.
"""
import concurrent.futures
import hashlib
import http.client
import importlib.metadata
import inspect
import json
import os
import pathlib
import socket
import socketserver
import ssl
import subprocess
import sys
import threading
import time
from types import SimpleNamespace

sys.path.insert(0, '/app')
OUT = pathlib.Path('/evidence')
events = []
release = threading.Event()
guard = threading.Lock()
blocked = 0
writes = []
violations = []

def record(event, **fields):
    with guard:
        events.append(dict(event=event, wall=time.time(), **fields))

def waitfor(predicate, timeout=15):
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        if predicate():
            return
        time.sleep(.05)
    raise AssertionError('fixture condition timed out')

# Ephemeral fixture-only certificate, never copied out of this container.
subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes',
    '-keyout','/tmp/fixture.key','-out','/tmp/fixture.crt','-days','1',
    '-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost,IP:127.0.0.1'],
    check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
tls.load_cert_chain('/tmp/fixture.crt','/tmp/fixture.key')

class RedisHandler(socketserver.StreamRequestHandler):
    def handle(self):
        global blocked
        while True:
            header = self.rfile.readline()
            if not header:
                return
            assert header.startswith(b'*'), header
            parts = []
            for _ in range(int(header[1:])):
                size = int(self.rfile.readline()[1:])
                parts.append(self.rfile.read(size))
                assert self.rfile.read(2) == b'\r\n'
            command = parts[0].upper()
            if command == b'EXISTS':
                with guard:
                    blocked += 1
                record('redis_exists_waiting')
                assert release.wait(180), 'fixture release missing'
                self.wfile.write(b':0\r\n')
                record('redis_exists_released')
            elif command in (b'CLIENT', b'SET', b'AUTH', b'SELECT'):
                self.wfile.write(b'+OK\r\n')
            elif command == b'PING':
                self.wfile.write(b'+PONG\r\n')
            else:
                raise AssertionError(command)
            self.wfile.flush()

class RedisServer(socketserver.ThreadingTCPServer):
    daemon_threads = True
    def get_request(self):
        sock, addr = super().get_request()
        return tls.wrap_socket(sock, server_side=True), addr

redis_server = RedisServer(('127.0.0.1',0),RedisHandler)
threading.Thread(target=redis_server.serve_forever, daemon=True).start()
redis_url = (f'rediss://127.0.0.1:{redis_server.server_address[1]}/0'
    '?ssl_cert_reqs=required&ssl_check_hostname=true&ssl_ca_certs=/tmp/fixture.crt')
os.environ.update(REDIS_URL=redis_url, INTERNAL_SECRET='fixture-internal-only',
    SUPABASE_URL='http://127.0.0.1:19991', SUPABASE_SERVICE_ROLE_KEY='synthetic-only',
    ANTHROPIC_API_KEY='')

def audit(event, args):
    if event == 'socket.connect' and (not isinstance(args[1],tuple) or args[1][0] not in ('127.0.0.1','::1')):
        violations.append(event)
        raise RuntimeError('non-loopback network denied')
    if event in ('subprocess.Popen','os.fork','os.posix_spawn'):
        violations.append(event)
        raise RuntimeError('application process spawn denied')
sys.addaudithook(audit)

from app.api.v1 import internal
from app.services import store_index
import redis
import uvicorn
from fastapi import FastAPI
from postgrest.constants import DEFAULT_POSTGREST_CLIENT_TIMEOUT
from curl_cffi import Curl
import curl_cffi.requests.utils
import httpcore._backends.sync
OUT.joinpath('library-source-evidence.txt').write_text('\n\n'.join([
    inspect.getsource(redis.connection.Connection._connect),
    inspect.getsource(redis.connection.SSLConnection._connect),
    inspect.getsource(redis.connection.SSLConnection._wrap_socket_with_ssl),
    inspect.getsource(curl_cffi.requests.utils.set_curl_options),
    inspect.getsource(httpcore._backends.sync.SyncBackend.connect_tcp),
    inspect.getsource(httpcore._backends.sync.SyncStream.read)]))

class Query:
    def __init__(self): self.operation='read'
    def __getattr__(self, name):
        def call(*args, **kwargs):
            if name in ('insert','update','upsert'): self.operation=name
            return self
        return call
    def execute(self):
        if self.operation != 'read':
            writes.append(time.time())
            record('fixture_db_write', operation=self.operation)
        return SimpleNamespace(data=None)
class DB:
    def table(self, name):
        assert name == 'shopify_store_index'
        return Query()
internal.get_supabase = lambda: DB()

class Response:
    status_code=200
    headers={'content-type':'application/json'}
    text='<title>Fixture</title>cdn.shopify.com window.Shopify'
    def __init__(self,url): self.url=url
    def json(self):
        if '/cart.js' in self.url: return {'token':'synthetic','currency':'USD'}
        if '/products.json' in self.url:
            return {'products':[{'id':1,'handle':'fixture','title':'Fixture',
                'variants':[{'price':'10'}]}]}
        return {'collections':[]}
class Merchant:
    def __init__(self,*args,**kwargs): pass
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def get(self,url,**kwargs): return Response(url)
assert store_index._USE_CURL_CFFI
store_index.CurlSession = Merchant

class Observe:
    def __init__(self,app): self.app=app
    async def __call__(self,scope,receive,send):
        if scope['type']!='http': return await self.app(scope,receive,send)
        record('request_started')
        try: return await self.app(scope,receive,send)
        finally: record('request_finished')
app=FastAPI()
app.include_router(internal.router,prefix='/api/v1')
app.add_middleware(Observe)
listener=socket.socket();listener.bind(('127.0.0.1',0))
port=listener.getsockname()[1]
server=uvicorn.Server(uvicorn.Config(app,log_level='error',lifespan='off'))
server_thread=threading.Thread(target=lambda:server.run(sockets=[listener]),daemon=True)
server_thread.start();waitfor(lambda:server.started)

def request(index):
    client=http.client.HTTPConnection('127.0.0.1',port,timeout=1)
    client.request('POST','/api/v1/internal/store-index/verify',
        body=json.dumps({'domain':f'fixture{index}.invalid'}),
        headers={'Content-Type':'application/json','x-internal-token':'fixture-internal-only'})
    try:
        client.getresponse()
        raise AssertionError('expected caller timeout')
    except TimeoutError:
        record('caller_timeout', operation=index)
    finally: client.close()

with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    list(pool.map(request,range(3)))
waitfor(lambda:blocked==3)
containment=time.time();record('fixture_no_more_ingress')
# This is deliberately NOT presented as a measured upper bound. Redis has
# socket_timeout=None, so the fixture can postpone release arbitrarily.
time.sleep(130)
assert len(writes)==0 and not any(e['event']=='request_finished' for e in events)
record('still_active_beyond120')
release.set()
waitfor(lambda:len(writes)==3)
waitfor(lambda:len([e for e in events if e['event']=='request_finished'])==3)
assert all(t>containment+120 for t in writes)
assert violations==[]
server.should_exit=True;server_thread.join(timeout=10)
assert not server_thread.is_alive()
redis_server.shutdown();redis_server.server_close()

client=redis.Redis.from_url(redis_url,socket_connect_timeout=1)
kwargs=client.connection_pool.connection_kwargs
summary=dict(passed=True,source='288223a2acb62bd6893e3370268f854bb2e16b12',
    curl_version=Curl().version().decode(),
    versions={n:importlib.metadata.version(n) for n in
        ['redis','httpx','httpcore','curl-cffi','supabase','postgrest','anyio','fastapi','uvicorn']},
    redis_response_timeout=kwargs.get('socket_timeout'),
    redis_connect_timeout=kwargs.get('socket_connect_timeout'),
    tls_cert_required=kwargs.get('ssl_cert_reqs')=='required',
    tls_hostname_checked=kwargs.get('ssl_check_hostname'),
    postgrest_timeout=DEFAULT_POSTGREST_CLIENT_TIMEOUT,
    concurrent_requests=3,fixture_writes=len(writes),violations=violations,
    last_write_seconds_after_containment=max(writes)-containment,events=events,
    source_hashes={p:hashlib.sha256(pathlib.Path('/app',p).read_bytes()).hexdigest()
        for p in ['app/api/v1/internal.py','app/services/store_index.py','app/services/fetch.py']})
OUT.joinpath('lifetime-counterexample.json').write_text(json.dumps(summary,indent=2))
print('LIFETIME_COUNTEREXAMPLE '+json.dumps(summary),flush=True)
