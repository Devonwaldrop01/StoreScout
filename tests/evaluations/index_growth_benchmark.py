"""Preserved endpoint/panel; vary real captured supply, never fabricate stores.

Usage: python tests/evaluations/index_growth_benchmark.py VARIANT [prior evidence root]
All outputs are new. Unknown placements are explicit, never counted as useful.
"""
import contextlib, io, json, os, runpy, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
prior=Path(sys.argv[2] if len(sys.argv)>2 else ROOT.parent/'storescout-phase1').resolve()
variant=sys.argv[1]
out=ROOT/'outputs/index-growth'
target=out/variant/'evidence'
load=lambda p:json.loads(p.read_text(encoding='utf8'))
clock=(load(ROOT/'docs/quality-audit/index-growth/funnel.json')['rows'][0]['measured_at'] if variant=='current'
       else load(prior/'outputs/bounded-cycle/clock.json')['clock'])
# Expanded observations occurred later on the same day; compare controlled and
# expanded at exactly the same later cutoff rather than making future facts usable.
if variant in ('controlled','expanded'):
    rows=load(prior/'outputs/production-access/index-after.json')
    clock=max([clock]+[(r.get('catalog_observation') or {}).get('observed_at') or '' for r in rows])
(out/'clock.json').write_text(json.dumps({'clock':clock}))
code=(ROOT/'tests/evaluations/bounded_cycle_benchmark.py').read_text(encoding='utf8')
code=code.replace("OUT=ROOT/'outputs/bounded-cycle'", "OUT=ROOT/'outputs/index-growth'")
code=code.replace("ROOT/'outputs/controlled-validation/after/evidence/relevance-labels.json'", repr(str(prior/'outputs/controlled-validation/after/evidence/relevance-labels.json')))
# load() accepts Path; the replacement above therefore needs a Path conversion.
code=code.replace('load('+repr(str(prior/'outputs/controlled-validation/after/evidence/relevance-labels.json'))+')', 'load(Path('+repr(str(prior/'outputs/controlled-validation/after/evidence/relevance-labels.json'))+'))')
with contextlib.redirect_stdout(io.StringIO()):
    exec(compile(code,'growth-replay','exec'),{'__file__':str(ROOT/'tests/evaluations/bounded_cycle_benchmark.py')})
labels=[]
for path in [ROOT/'docs/quality-audit/real-world/evidence/relevance-labels.json',
             prior/'outputs/bounded-cycle/frozen/evidence/relevance-labels.json',
             prior/'outputs/bounded-cycle/controlled/evidence/relevance-labels.json']:
    labels.extend(load(path))
lookup={(x['case_id'],x['mode'],x['domain']):x for x in labels}
extra=ROOT/'docs/quality-audit/index-growth/new-judgments.json'
if extra.exists():
    lookup.update({(x['case_id'],x['mode'],x['domain']):x for x in load(extra)})
runs=load(target/'replay-results.json'); reviewed=[]; missing=[]
if variant == 'current':
    # This export contains verified rows only. Absence here does not mean that
    # the reference domain is absent from the full 40,010-row production index.
    for case in runs:
        for ref in case['references']:
            if ref['stage'] == 'absent_from_index': ref['stage'] = 'absent_from_verified_export'
    (target/'replay-results.json').write_text(json.dumps(runs,indent=2))
for c in runs:
    for rank,domain in enumerate(c['returned_domains'],1):
        key=c['case_id'],c['mode'],domain
        label=lookup.get(key)
        if label is None:
            label={'case_id':c['case_id'],'mode':c['mode'],'domain':domain,'label':None,'reason':'Unadjudicated; excluded from useful count'}
            missing.append({**label,'query':c['query'],'rank':rank})
        reviewed.append({**label,'rank':rank})
(target/'relevance-labels.json').write_text(json.dumps(reviewed,indent=2))
(target.parent/'pending.json').write_text(json.dumps(missing,indent=2))
os.chdir(target.parent)
with contextlib.redirect_stdout(io.StringIO()):runpy.run_path(str(ROOT/'docs/quality-audit/real-world/evidence/measure.py'))
from app.services.discovery_quality import is_recent_verified,is_classification_usable
from datetime import datetime
stamp=datetime.fromisoformat(clock)
supply=sum(is_recent_verified(r,now=stamp) and is_classification_usable(r,now=stamp) for r in load(target/'index-snapshot.json'))
metrics=load(target/'benchmark-metrics.json')
metrics['benchmark']=f'Unchanged reviewed retrieval/ranking; {variant} captured supply; clock={clock}'
metrics['usable_supply']=supply
metrics['unadjudicated_placements']=len(missing)
(target/'benchmark-metrics.json').write_text(json.dumps(metrics,indent=2))
print(json.dumps({'variant':variant,'usable_supply':supply,'pending':len(missing),'summary':{mode:value['core24'] for mode,value in metrics['summary'].items()}},indent=2))
