"""OFFLINE ONLY. Real route/executor/verification code; synthetic external dependencies."""
import atexit, asyncio, concurrent.futures, hashlib, inspect, json, os, pathlib, sys, threading, time
from types import SimpleNamespace

started=time.monotonic()
def event(kind, **data):
    print('DRAIN_EVENT '+json.dumps(dict(event=kind,wall=time.time(),elapsed=round(time.monotonic()-started,6),pid=os.getpid(),**data)),flush=True)

violations=[]
def audit(kind,args):
    if kind in ('socket.connect','subprocess.Popen','os.system','os.fork','os.posix_spawn'):
        violations.append(kind);event('forbidden_operation',operation_kind=kind)
        raise RuntimeError('offline test forbids network/process operations')
sys.addaudithook(audit)

from uvicorn.server import Server
original_exit=Server.handle_exit
def handle_exit(self,sig,frame):
    event('term_received',signal=sig)
    return original_exit(self,sig,frame)
Server.handle_exit=handle_exit

shutdown=concurrent.futures.ThreadPoolExecutor.shutdown
def executor_shutdown(self,*args,**kwargs):
    event('executor_shutdown_begin',wait=kwargs.get('wait',args[0] if args else True),threads=[dict(name=t.name,daemon=t.daemon,alive=t.is_alive()) for t in self._threads])
    result=shutdown(self,*args,**kwargs)
    event('executor_shutdown_end')
    return result
concurrent.futures.ThreadPoolExecutor.shutdown=executor_shutdown

# Observe actual function entry/return, without replacing its implementation.
def profile(frame,what,arg):
    if frame.f_code.co_name=='verify_shopify' and frame.f_code.co_filename.endswith('/app/services/fetch.py'):
        if what=='call':event('verify_start',domain=frame.f_locals.get('domain'),thread=threading.current_thread().name,daemon=threading.current_thread().daemon)
        if what=='return':event('verify_complete',domain=frame.f_locals.get('domain'))
threading.setprofile(profile)

# Uvicorn adds its app-dir later; the test hook runs earlier during site startup.
# Match that same /app import directory without modifying the retained image.
sys.path.insert(0,'/app')
import app.main
import app.api.v1.competitors as competitors
import app.services.fetch as fetch
import anthropic
import redis
from celery.app.task import Task

durations=[float(x) for x in os.environ['FIXTURE_DURATIONS'].split(',')]
class Query:
    def __init__(self,table):self.table=table;self.single=False;self.write=False
    def __getattr__(self,name):
        def call(*a,**kw):
            if name in ('maybe_single','single'):self.single=True
            if name in ('upsert','insert','update','delete'):self.write=True
            return self
        return call
    def execute(self):
        if self.write:event('fixture_db_write',table=self.table)
        return SimpleNamespace(data=({'tier':'pro'} if self.table=='user_profiles' else None) if self.single else [])
class DB:
    def table(self,name):return Query(name)
competitors.get_supabase=lambda:DB()
app.main.app.dependency_overrides[competitors.get_current_user_id]=lambda:'fixture-user'
competitors.get_settings().anthropic_api_key='synthetic-only'

ai_calls=0
class Messages:
    def create(self,**kwargs):
        global ai_calls
        ai_calls+=1
        data=[{'domain':f'fixture{i}.invalid','reason':'offline fixture'} for i in range(len(durations))] if ai_calls==1 else []
        return SimpleNamespace(content=[SimpleNamespace(text=json.dumps({'suggestions':data}))])
anthropic.Anthropic=lambda **kw:SimpleNamespace(messages=Messages())
class FakeRedis:
    def set(self,*a,**kw):event('fixture_redis_set');return False
redis.from_url=lambda *a,**kw:FakeRedis()
def fake_dispatch(self,*a,**kw):event('fixture_queue_dispatch',task=self.name);return None
Task.apply_async=fake_dispatch

class Response:
    status_code=200
    headers={'content-type':'application/json'}
    text='cdn.shopify.com window.Shopify'
    def __init__(self,url):self.url=url
    def json(self):return {'products':[{'id':1}]} if '/products.json' in self.url else {'token':'synthetic'}
class Catalog:
    def __init__(self,*a,**kw):pass
    def __enter__(self):return self
    def __exit__(self,*a):pass
    def get(self,url,**kwargs):
        if '/products.json' in url:
            index=int(url.split('fixture')[1].split('.')[0]);end=time.monotonic()+durations[index]
            while time.monotonic()<end:
                event('executor_activity',operation=index)
                time.sleep(min(.5,max(.001,end-time.monotonic())))
            # Represents a final operation performed by the still-live executor.
            event('fixture_write_capability',operation=index)
        return Response(url)
assert fetch._USE_CURL_CFFI is True
fetch.CurlSession=Catalog

class ObserveHTTP:
    def __init__(self,app):self.app=app
    async def __call__(self,scope,receive,send):
        if scope['type']!='http':return await self.app(scope,receive,send)
        event('request_started',loop=type(asyncio.get_running_loop()).__module__+'.'+type(asyncio.get_running_loop()).__name__)
        async def output(msg):
            if msg['type']=='http.response.start':event('http_response',status=msg['status'])
            await send(msg)
        try:await self.app(scope,receive,output)
        finally:event('request_finished')
app.main.app.add_middleware(ObserveHTTP)

# Trace only the exception edge of the ORIGINAL nested function to date the timeout.
def trace(frame,what,arg):
    if frame.f_code.co_filename.endswith('/app/api/v1/competitors.py') and frame.f_code.co_name=='_verify':
        if what=='exception' and isinstance(arg[1],TimeoutError):event('request_verification_timeout',domain=frame.f_locals.get('domain'))
    return trace
sys.settrace(trace)

def final():
    event('interpreter_atexit',violations=violations,threads=[dict(name=t.name,daemon=t.daemon,alive=t.is_alive()) for t in threading.enumerate()])
atexit.register(final)
event('fixture_ready',source_hashes={p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest() for p in ('app/main.py','app/api/v1/competitors.py','app/services/fetch.py')})
