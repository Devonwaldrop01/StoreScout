"""Offline captured-catalog batch replay. No credentials/network; no new stores.

Run from repository root with Python -X utf8. Prior raw captures are local inputs.
"""
from pathlib import Path
import collections, json, os, socket, sys, time
from copy import deepcopy
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT/'tests')]
os.environ['STORE_INDEX_DEPLOYMENT_HOLD'] = 'false'  # this offline process only
os.environ['ANTHROPIC_API_KEY'] = ''
import app.core.config as config
settings = config.Settings(_env_file=None, anthropic_api_key='', redis_url='',
    supabase_url='', supabase_service_role_key='')
config.get_settings = lambda: settings
def forbidden(*a, **k): raise AssertionError('Network forbidden in captured replay')
socket.socket.connect = forbidden
socket.getaddrinfo = forbidden
from app.services import store_index as index, store_dna as dna, runtime_config
from app.tasks import store_index as tasks
from test_index_growth import SelectedDB, SelectedQuery
from app.services.discovery_quality import is_classification_usable
from datetime import datetime
import anthropic
anthropic.Anthropic = forbidden
# Real no-key paths: deterministic classification and heuristic DNA. The
# Anthropic constructor and every socket are forbidden as a second guard.
runtime_config.get_config = lambda k, default=None: default
load = lambda p: json.loads(p.read_text(encoding='utf8'))
prior = ROOT.parent/'storescout-phase1/outputs'
records = load(prior/'production-access/outcomes.json')
rows = [deepcopy(r['verified_row']) for r in records if r['result'].get('outcome') == 'verified']
for r in rows:
    r['knowledge_at'] = None
    assert r.get('updated_at') and r.get('catalog_observation')
original = SelectedQuery.select
results = {}
for variant in ('before_missing_version', 'after_version_preserved'):
    db = SelectedDB(rows)
    tasks.get_supabase = lambda: db
    def selected(self, columns, **kwargs):
        if variant == 'before_missing_version': columns = columns.replace('updated_at, ', '')
        return original(self, columns, **kwargs)
    SelectedQuery.select = selected
    start = time.perf_counter()
    result = tasks.stage_knowledge.run.__wrapped__(force=True)
    elapsed = time.perf_counter()-start
    completed = [r for r in db.rows.values() if r.get('updated_at') != next(x['updated_at'] for x in rows if x['domain']==r['domain'])]
    results[variant] = {'batch': result, 'seconds': elapsed, 'persisted': len(completed),
        'confidence_distribution': dict(collections.Counter(r.get('category_confidence') for r in completed)),
        'confidence_pass': sum((r.get('category_confidence') or 0)>=55 for r in completed),
        'classification_usable': sum(is_classification_usable(r) for r in completed)}
SelectedQuery.select = original
# Replay response metadata/body through the actual protection detector. This
# estimates calls suppressed, not a new network success rate.
protection = {}
from types import SimpleNamespace
for name in ('controlled-validation', 'production-access'):
    rs = load(prior/name/'outcomes.json')
    suppressed = total = affected = successes_affected = missing_bodies = 0
    for r in rs:
        reqs = r.get('requests', [])
        total += len(reqs)
        for i, req in enumerate(reqs):
            if '/collections.json' in req['url']:
                continue  # optional final hint; readable catalog already established
            body = ''
            if req.get('body_file'):
                path = (prior/name/'raw'/req['body_file']).resolve()
                if os.name == 'nt': path = Path('\\\\?\\' + str(path))
                try: body = path.read_text(encoding='utf8', errors='replace')
                except OSError: missing_bodies += 1  # retain status-only evidence
            response = SimpleNamespace(status_code=req.get('status',0), text=body, headers=req.get('headers',{}))
            if index._protection_result(response, {}) is not None:
                suppressed += len(reqs)-i-1
                affected += 1
                successes_affected += (r.get('result') or {}).get('outcome')=='verified'
                break
    protection[name] = {'assigned':len(rs),'recorded_logical_calls':total,
        'domains_with_stop':affected,'later_recorded_calls_suppressed':suppressed,
        'previous_successes_with_stop':successes_affected, 'missing_bodies':missing_bodies,
        'scope':'offline recorded endpoint sequence; no claim about new access yield'}
out = {'classification':results, 'protection':protection,
       'network_calls':0,'paid_AI_calls':0,'production_writes':0,
       'classification_sample':'36 successful public catalogs retained from prior bounded access validation; not random production yield'}
target=ROOT/'docs/quality-audit/index-growth/offline-measurements.json'
target.write_text(json.dumps(out,indent=2),encoding='utf8')
print(json.dumps(out,indent=2))
