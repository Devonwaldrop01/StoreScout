import json, pathlib, hashlib, collections, datetime, random, socket, ipaddress, urllib.parse, time, concurrent.futures, re, threading, urllib.request, urllib.error
from html.parser import HTMLParser
class Parser(HTMLParser):
 def __init__(self,text):
  super().__init__();self.parts=[];self.title_parts=[];self.skip=0;self.in_title=False;self.canonical=None;self.feed(text)
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag in ('script','style','noscript','svg'):self.skip+=1
  if tag=='title':self.in_title=True
  if tag=='link' and a.get('rel')=='canonical':self.canonical=a.get('href')
 def handle_endtag(self,tag):
  if tag in ('script','style','noscript','svg'):self.skip=max(0,self.skip-1)
  if tag=='title':self.in_title=False
 def handle_data(self,data):
  if not self.skip:self.parts.append(data)
  if self.in_title:self.title_parts.append(data)
 def text(self):return ' '.join(' '.join(self.parts).split())
 def title(self):return ' '.join(self.title_parts).strip() or None
P=pathlib.Path('evidence'); rows=json.loads((P/'index-snapshot.json').read_text()); results=json.loads((P/'replay-results.json').read_text())
clock=datetime.datetime.fromisoformat('2026-09-05T20:44:23.705755+00:00')
def age(r):
 s=r.get('last_verified_at')
 if not s:return 'missing'
 days=(clock-datetime.datetime.fromisoformat(s)).total_seconds()/86400
 return 'future' if days<0 else '0-7' if days<=7 else '8-30' if days<=30 else '31-60' if days<=60 else '>60'
strata=collections.defaultdict(list)
for r in rows:strata[(r.get('category') or 'UNCLASSIFIED',r['status'],age(r))].append(r['domain'])
# Reproducible stratified 240-row sample: one per stratum, distribute remainder by population size.
target=240;alloc={k:1 for k in strata}
while sum(alloc.values())<target:
 k=max((k for k in strata if alloc[k]<len(strata[k])),key=lambda k:len(strata[k])/alloc[k]);alloc[k]+=1
sample=[]
for k,domains in sorted(strata.items()):
 chosen=sorted(domains,key=lambda d:hashlib.sha256(('StoreScout-census-20260905-v1:'+d).encode()).hexdigest())[:alloc[k]]
 sample.extend({'domain':d,'stratum':k,'N':len(domains),'n':alloc[k],'inclusion_probability':alloc[k]/len(domains),'weight':len(domains)/alloc[k]} for d in chosen)
(P/'health-sample.json').write_text(json.dumps(sample,indent=2))
references={r['domain'] for c in results for r in c['references']}|{c['domain'] for c in results}
returned={d for c in results for d in c['returned_domains']}
domains=sorted(references|returned|{r['domain'] for r in sample},key=lambda d:hashlib.sha256(('blind-review:'+d).encode()).hexdigest())
(P/'public-observations').mkdir(exist_ok=True)
dns_cache={}
def allowed(url):
 u=urllib.parse.urlsplit(url)
 if u.scheme not in ('http','https') or u.username or u.password or not u.hostname or (u.port and u.port not in (80,443)):raise ValueError('unsafe_url')
 host=u.hostname.lower()
 if host in ('localhost','metadata.google.internal') or host.endswith(('.local','.internal','.localhost')):raise ValueError('non_public_destination')
 try:addresses=[str(ipaddress.ip_address(host))]
 except ValueError:
  if host not in dns_cache:
   du='https://cloudflare-dns.com/dns-query?'+urllib.parse.urlencode({'name':host,'type':'A'})
   with urllib.request.urlopen(urllib.request.Request(du,headers={'Accept':'application/dns-json'}),timeout=12) as dr:
    dj=json.loads(dr.read(40000));dns_cache[host]=[x['data'] for x in dj.get('Answer',[]) if x.get('type')==1]
  addresses=dns_cache[host]
 if not addresses or any(not ipaddress.ip_address(x).is_global for x in addresses):raise ValueError('no_public_ipv4_dns')
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None
def get(url,cap=700000):
 chain=[];opener=urllib.request.build_opener(NoRedirect)
 for hop in range(6):
  allowed(url)
  req=urllib.request.Request(url,headers={'User-Agent':'StoreScout-ReadOnly-Research/1.0','Accept':'text/html,application/json'})
  try:r=opener.open(req,timeout=12)
  except urllib.error.HTTPError as e:r=e
  with r:
   code=r.status;chain.append({'url':url,'status':code})
   if code in (301,302,303,307,308) and r.headers.get('Location'):
    url=urllib.parse.urljoin(url,r.headers['Location']);continue
   data=r.read(cap+1)
   return {'url':url,'status':code,'chain':chain,'truncated':len(data)>cap,'body':data[:cap].decode(r.headers.get_content_charset() or 'utf-8',errors='replace'),'content_type':r.headers.get('Content-Type','')}
 raise ValueError('redirect_limit')
def observe(domain,attempt=1):
 path=P/'public-observations'/(hashlib.sha256(domain.encode()).hexdigest()+'.json')
 if path.exists() and attempt==1:return json.loads(path.read_text())
 o={'domain':domain,'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'attempt':attempt,'population_sample':domain in {x['domain'] for x in sample},'checks':{}}
 for kind,url in [('home','https://'+domain),('products','https://'+domain+'/products.json?limit=50&page=1')]:
  try:
   a=get(url);body=a.pop('body');low=body.lower()
   a['shopify_markers']=[s for s in ['cdn.shopify.com','shopify.theme','shopify-checkout','myshopify.com','shopify-section'] if s in low]
   a['password_signal']=('/password' in a['url'] or 'shopify-section-main-password' in low or ('opening soon' in low and 'password' in low))
   a['challenge_signal']=any(s in low for s in ['just a moment...','verify you are human','checking your browser','attention required! | cloudflare'])
   a['parking_signal']=any(s in low for s in ['this domain is for sale','buy this domain','domain parking','sedo domain parking','domain is parked'])
   if kind=='products':
    try:
     js=json.loads(body);prods=js.get('products') if isinstance(js,dict) else None
     a['readable_catalog']=isinstance(prods,list)
     if isinstance(prods,list):a['products']=[{'title':p.get('title'),'product_type':p.get('product_type'),'tags':p.get('tags'),'handle':p.get('handle'),'description':Parser(p.get('body_html') or '').text()[:1800]} for p in prods]
    except (ValueError,TypeError):a['readable_catalog']=False
   soup=Parser(body)
   a['title']=soup.title()
   a['canonical']=soup.canonical
   a['text']=soup.text()[:35000] if kind=='home' or not a.get('readable_catalog') else None
   o['checks'][kind]=a
  except Exception as e:o['checks'][kind]={'error':type(e).__name__+': '+str(e)[:250]}
 h=o['checks']['home'];p=o['checks']['products']
 o['accessible_home']=h.get('status',0) in range(200,300) and not h.get('challenge_signal',False)
 o['readable_nonempty_catalog']=bool(p.get('readable_catalog') and p.get('products'))
 o['shopify_evidence']=bool(h.get('shopify_markers') or p.get('shopify_markers') or o['readable_nonempty_catalog'])
 o['password_signal']=bool(h.get('password_signal') or p.get('password_signal'))
 o['parking_signal']=bool(h.get('parking_signal') or p.get('parking_signal'))
 o['unknown_access']=not o['accessible_home'] and not o['readable_nonempty_catalog']
 if attempt>1:o['previous_attempt']=json.loads(path.read_text())
 path.write_text(json.dumps(o,ensure_ascii=False,indent=2));return o
print('Population strata',len(strata),'sample',len(sample),'total independent domains',len(domains),flush=True)
observed=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
 for i,o in enumerate(pool.map(observe,domains),1):
  observed.append(o)
  if i%20==0:print('Observed',i,'/',len(domains),flush=True)
retry=[o['domain'] for o in observed if o['unknown_access'] and any('error' in x for x in o['checks'].values())]
print('Later-window retries',len(retry),flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:list(pool.map(lambda d:observe(d,2),retry))
print('Public checks complete',flush=True)
