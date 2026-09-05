"""Offline StoreScout audit reproductions, prepared 2026-09-05.

Reviewed commit: e66e3f05417cea5d57f27800c755c2353ca2b791
Usage: python StoreScout-Audit-Reproductions.py /absolute/path/to/StoreScout

Reads source without modifying the checkout. HTTP, database and payment
boundaries are faked. Some functions are extracted via AST with decorators
removed; this is not an integration or security penetration test. Prints JSON
observations rather than making network calls. Intended for the reviewed commit;
function changes may require updating the probes.
"""
import ast, asyncio, json, logging, math, re, sys, time, traceback
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
from collections import Counter
from statistics import median
from typing import Any, Dict, List, Optional
if len(sys.argv) != 2:
 raise SystemExit("Usage: python StoreScout-Audit-Reproductions.py /absolute/path/to/StoreScout")
ROOT = Path(sys.argv[1]).expanduser().resolve(strict=True)
if not (ROOT / "app/services/normalize.py").is_file():
 raise SystemExit("The argument must be the StoreScout repository root.")
sys.path.insert(0,str(ROOT))
logging.disable(logging.CRITICAL)
results=[]
def functions(path,names,ns):
 tree=ast.parse((ROOT/path).read_text())
 nodes=[]
 for node in tree.body:
  if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name in names:
   node.decorator_list=[]
   nodes.append(node)
 unit=ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0)]+nodes,type_ignores=[])
 exec(compile(ast.fix_missing_locations(unit),str(ROOT/path),'exec'),ns)
 return ns
from app.services.normalize import normalize_product
from app.services.analyze import analyze_products
p=normalize_product({'id':1,'handle':'sample','title':'Sample','variants':[{'price':'10','compare_at_price':None,'available':True},{'price':'100','compare_at_price':'100','available':True}]},'https://example.com')
a=analyze_products([p])
results.append({'check':'Variant-mismatched discount','observed':{'discount_pct_min':p['discount_pct_min'],'discounted_pct':a['discounts']['discounted_pct']},'expected':'Neither variant has a markdown; discounted share should be 0%.'})
try:
 normalize_product({'variants':[{'price':'invalid'},{'price':'10'}]},'https://example.com')
 results.append({'check':'Malformed numeric price','observed':'No error'})
except Exception as e: results.append({'check':'Malformed numeric price','observed':type(e).__name__+': '+str(e),'expected':'Ignore invalid value; report lower coverage.'})
ns=globals().copy()
ns.update(PRICE_CHANGE_THRESHOLD_PCT=3.0,FLASH_SALE_MIN_PRODUCTS=5,FLASH_SALE_MIN_AVG_DROP_PCT=20.0,DISCOUNT_RATE_SWING_PCT=10.0)
functions(Path('app/tasks/detect_changes.py'),['_product_index','_detect'],ns)
old={'_product_index':{'a':{'title':'A','price_min':10},'b':{'title':'B','price_min':20}},'catalog_truncated':True}
new={'_product_index':{'a':{'title':'A','price_min':10}},'catalog_truncated':True}
results.append({'check':'Incomplete snapshots generate removal','observed':ns['_detect'](old,new),'expected':'No confirmed removal from non-exhaustive snapshots.'})
class Client:
 def __enter__(self): return self
 def __exit__(self,*args): pass
 def get(self,url,**kwargs):
  first='page=1' in url
  return SimpleNamespace(status_code=200 if first else 503,headers={'content-type':'application/json'},url=url,text='{}',json=lambda:{'products':[{'id':1,'handle':'a'}]})
ns=globals().copy();ns.update(logger=logging.getLogger('audit'),_USE_CURL_CFFI=True,IMPERSONATE='stub',DEFAULT_HEADERS={'User-Agent':'offline-audit'},_enforce_domain_rate_limit=lambda x:None,_headers=lambda:{},CurlSession=lambda **kw:Client(),_classify_failure=lambda *a:'503')
functions(Path('app/services/fetch.py'),['fetch_products_shopify'],ns)
partial=ns['fetch_products_shopify']('https://example.com',1500)
results.append({'check':'Page two 503 returns success-shaped list','observed':partial,'expected':'Distinct incomplete/error result; do not publish as full scan.'})
class DB:
 def __init__(self): self.kind='';self.writes=[];self.change=None
 def table(self,x): self.kind=x;self.change=None;return self
 def select(self,*a,**k):return self
 def eq(self,*a,**k):return self
 def maybe_single(self):return self
 def order(self,*a,**k):return self
 def limit(self,*a,**k):return self
 def update(self,value):self.change=value;self.writes.append(value);return self
 def execute(self):
  if self.change is not None:return SimpleNamespace(data=[])
  if self.kind=='competitors':return SimpleNamespace(data={'store_url':'https://example.com','hostname':'example.com','user_profiles':{'tier':'pro'}})
  return SimpleNamespace(data=[{'snapshot_data':{'lists':{'recently_updated':[{'updated_at':'2026-09-01T00:00:00Z'}]}}}])
db=DB();calls=[]
def fake_fetch(url,max_products=None):
 calls.append(max_products)
 all_products=[{'id':1,'updated_at':'2026-09-01T00:00:00Z'},{'id':2,'updated_at':'2026-09-05T00:00:00Z','price':'5'}]
 return all_products[:max_products] if max_products else all_products
ns=globals().copy();ns.update(logger=logging.getLogger('audit'),get_settings=lambda:SimpleNamespace(),get_supabase=lambda:db,_require_internal=lambda x:None,fetch_products_shopify=fake_fetch,_interval_for_tier=lambda *a:24,Header=lambda *a:None)
functions(Path('app/api/v1/internal.py'),['internal_scan'],ns)
results.append({'check':'One-product probe misses another product change','observed':ns['internal_scan']('synthetic-id','stub'),'fetch_limits':calls,'expected':'Full scan or a catalog-wide change token.'})
class Req:
 headers={'stripe-signature':'stub'}
 async def body(self):return b'{}'
def fail(*a): raise RuntimeError('Synthetic DB failure')
ns=globals().copy();ns.update(logger=logging.getLogger('audit'),get_settings=lambda:SimpleNamespace(stripe_webhook_secret='stub'),get_supabase=lambda:object(),stripe=SimpleNamespace(Webhook=SimpleNamespace(construct_event=lambda *a:{'type':'checkout.session.completed','data':{'object':{}}})),_handle_event=fail)
functions(Path('app/api/v1/webhooks.py'),['stripe_subscription_webhook'],ns)
results.append({'check':'Payment handler failure acknowledged','observed':asyncio.run(ns['stripe_subscription_webhook'](Req())),'expected':'Retryable failure or durable queued work before success acknowledgement.'})
print(json.dumps(results,indent=2))
