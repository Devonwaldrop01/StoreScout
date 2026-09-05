import sys, pathlib, json, socket, types, asyncio, copy, hashlib
from datetime import datetime, timezone
ROOT=pathlib.Path(__file__).resolve().parents[4]  # StoreScout checkout containing this evidence
sys.path.insert(0,str(ROOT))
class Forbidden(BaseException): pass
attempts=[]
def deny(*a,**k):
    attempts.append(str(a[:1])); raise Forbidden('External access or mutation forbidden')
socket.socket.connect=deny; socket.socket.connect_ex=deny; socket.create_connection=deny
import app.core.config as config
settings=config.Settings(_env_file=None,anthropic_api_key='',supabase_url='',supabase_service_role_key='',shopify_index_min_confidence=60,shopify_index_category_min_confidence=55)
config.get_settings=lambda:settings
import app.api.v1.competitors as endpoint
import app.services.fetch as fetch
fetch.verify_shopify=deny
endpoint._anthropic.Anthropic=deny
from app.services import discovery_quality as quality
clock=datetime.fromisoformat('2026-09-05T20:44:23.705755+00:00')
class FrozenDate(datetime):
    @classmethod
    def now(cls,tz=None): return clock if tz else clock.replace(tzinfo=None)
quality.datetime=FrozenDate; endpoint.datetime=FrozenDate
rows=json.loads(pathlib.Path('evidence/index-snapshot.json').read_text())
by_domain={r['domain']:r for r in rows}
normalized={}
for r in rows:normalized.setdefault(r['domain'].lower().removeprefix('www.'),[]).append(r)
channels=json.loads(pathlib.Path('evidence/retrieval-postgres.json').read_text())['channels']
channel_map={(x['case_id'],x['channel']):x for x in channels}
panel=json.loads((ROOT/'docs/quality-audit/real-world/reference-panel.json').read_text())
plans=json.loads(pathlib.Path('evidence/replay-plan.json').read_text())
class Query:
    def __init__(self,db,table):self.db=db;self.table=table;self.columns='*';self.filters=[];self.single=False;self.ops=[]
    def select(self,cols,*a,**k):self.columns=cols;return self
    def maybe_single(self):self.single=True;return self
    def __getattr__(self,name):
        if name in ('update','upsert','insert','delete','rpc'):return deny
        if name not in ('eq','gte','lt','in_','order','limit','or_','overlaps'):raise AttributeError(name)
        def op(*a,**k):self.ops.append((name,a,k));return self
        return op
    def execute(self):
        if self.table=='user_profiles': data={'tier':'pro'}
        elif self.table=='business_profiles': data=self.db.profile or None
        elif self.table in ('competitors','competitor_edges'):data=None if self.single else []
        elif self.table=='shopify_store_index':
            if any(op[0]=='overlaps' for op in self.ops):
                self.db.trace.append({'channel':'dna','error':'Postgres 42883: operator does not exist for jsonb overlap','ops':self.ops})
                raise RuntimeError('operator does not exist: jsonb && array')
            channel='category' if any(op[0]=='eq' and op[1][0]=='category' for op in self.ops) else 'lexical'
            c=channel_map[(self.db.case['id'],channel)]
            expected_terms=self.db.case['terms']
            for op,args,kwargs in self.ops:
                if op=='eq' and args[0]=='category':assert args[1]==self.db.case['user_category']
                if op=='or_':assert args[0]==','.join(f'{col}.ilike.%{t}%' for t in expected_terms for col in ('category','subcategory','description','brand_name'))
                if op=='gte':assert args==('verification_confidence',60)
                if op=='limit':assert args==(200,)
            cols=[x.strip() for x in self.columns.split(',')]
            data=[{k:copy.deepcopy(by_domain[d].get(k)) for k in cols} for d in c['domains'] or []]
            self.db.trace.append({'channel':channel,'columns':cols,'ops':self.ops,'matched_count':c['matched_count'],'domains':c['domains'] or []})
        else:raise Forbidden('Unrecognized table '+self.table)
        return types.SimpleNamespace(data=data)
class DB:
    def __init__(self,case,profile):self.case=case;self.profile=profile;self.trace=[]
    def table(self,name):return Query(self,name)
    rpc=deny
out=[]
for mode in ('description_only','structured_profile'):
 for c in plans:
    source=panel['sources'][c['domain']]
    profile={} if mode=='description_only' else {'sells':c['query'],'notes':source['evidence_summary']}
    db=DB(c,profile); endpoint.get_supabase=lambda:db
    captured={}
    def trace(frame,event,arg):
        if frame.f_code.co_name=='discover_ai' and event=='return':
            for key in ('user_category','user_match_ctx','terms','idx_rows','_by_domain','ranked','verified','seen','blocked'):
                if key in frame.f_locals: captured[key]=copy.deepcopy(frame.f_locals[key])
        return trace
    sys.settrace(trace)
    error=None; response=None
    try:response=asyncio.run(endpoint.discover_ai(endpoint.DiscoverAIRequest(description=c['query']),user_id='benchmark-local-pro'))
    except endpoint.HTTPException as e:error={'status':e.status_code,'detail':e.detail}
    finally:sys.settrace(None)
    assert not attempts,attempts
    ranked=[]
    final=[r['domain'] for r in (response or {}).get('data',{}).get('suggestions',[])]
    for i,r in enumerate(captured.get('ranked',[]),1):
        m=quality.relevance(r,captured.get('user_match_ctx'))
        reasons=[]
        if not quality.is_recent_verified(r,60):reasons.append('fresh_catalog_gate')
        if not m['matched_terms']:reasons.append('no_matched_product_terms')
        if r.get('category_confidence') is not None and r['category_confidence']<55:reasons.append('category_confidence_floor')
        ranked.append({'domain':r['domain'],'pre_filter_rank':i,'match':m,'exclusions':reasons,'returned_rank':final.index(r['domain'])+1 if r['domain'] in final else None})
    refs=[]
    for ref in c['reference_set']:
        d=ref['domain'];r=by_domain.get(d) or next(iter(normalized.get(d,[])),None);rr=next((x for x in ranked if x['domain']==d),None)
        stage='absent_from_index' if r is None else 'not_verified' if r['status']!='verified' else 'fresh_catalog_gate' if not quality.is_recent_verified(r,60) else 'category_confidence_floor' if r.get('category_confidence') is not None and r['category_confidence']<55 else 'not_retrieved' if rr is None else 'no_matched_product_terms' if 'no_matched_product_terms' in rr['exclusions'] else 'returned' if d in final else 'below_top8'
        refs.append({'domain':d,'stage':stage,'index_domain':r.get('domain') if r else None,'index_status':r.get('status') if r else None,'rank':rr})
    out.append({'case_id':c['id'],'business':c['business'],'domain':c['domain'],'niche':c['niche'],'role':c['evaluation_role'],'mode':mode,'query':c['query'],'profile':profile,'classification':c['classification'],'user_category':captured.get('user_category'),'user_match_ctx':captured.get('user_match_ctx'),'retrieval':db.trace,'ranked':ranked,'references':refs,'response':response,'error':error,'returned_domains':final})
pathlib.Path('evidence/replay-results.json').write_text(json.dumps(out,indent=2))
print(json.dumps([{'case':x['case_id'],'mode':x['mode'],'results':x['returned_domains'],'refs':[(r['domain'],r['stage']) for r in x['references']]} for x in out if x['mode']=='description_only'],indent=2))
