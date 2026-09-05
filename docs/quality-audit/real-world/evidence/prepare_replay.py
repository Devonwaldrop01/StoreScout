import sys, pathlib, json, socket, types
ROOT=pathlib.Path(__file__).resolve().parents[4]  # StoreScout checkout containing this evidence
sys.path.insert(0,str(ROOT))
def deny(*a,**k): raise RuntimeError('NETWORK DISABLED FOR REPLAY')
socket.socket.connect=deny
socket.socket.connect_ex=deny
socket.create_connection=deny
import app.core.config as config
config.get_settings=lambda: config.Settings(_env_file=None,anthropic_api_key='',supabase_url='',supabase_service_role_key='')
from app.services.store_index import classify_store_v2
from app.services.store_dna import normalize_keywords
panel=json.loads((ROOT/'docs/quality-audit/real-world/reference-panel.json').read_text())
plan=[]
for c in panel['cases']:
    cl=classify_store_v2(description=c['query'],homepage_text=c['query'])
    cat=cl['category'] if cl.get('confidence',0)>=45 and cl['category']!='Other' else None
    plan.append({**c,'classification':cl,'user_category':cat,'terms':normalize_keywords(c['query'],limit=8)})
pathlib.Path('evidence/replay-plan.json').write_text(json.dumps(plan,indent=2))
print(json.dumps([{'case':c['id'],'category':c['user_category'],'terms':c['terms']} for c in plan],indent=2))
