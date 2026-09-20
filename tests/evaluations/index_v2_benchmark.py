"""Frozen 25-business endpoint/metrics; only input supply changes.

First export via index_v2.cli, then run index_growth_retrieval.mjs with the
exported experiment.json as its second user argument. This command consumes
those PostgreSQL channels, using existing judgments plus optional new labels.
Unknown placements are never credited. This is offline and never calls V2/legacy
production endpoints. Usage: python -X utf8 .../index_v2_benchmark.py EXPORT_DIR
"""
import contextlib,io,json,os,runpy,sys,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(sys.argv[1]).resolve()
if len(sys.argv)==2:
    # Each frozen replay installs permanent no-network guards. Isolate variants
    # so those guards cannot break a later Windows asyncio loop's wakeup pipe.
    for name in ('legacy','v2','combined'):
        subprocess.run([sys.executable,'-X','utf8',str(Path(__file__).resolve()),str(OUT),name],check=True)
    raise SystemExit(0)
if sys.argv[2] not in ('legacy','v2','combined'): raise ValueError('Unknown variant')
load=lambda p:json.loads(p.read_text(encoding='utf8'))
labels=[]
for file in [ROOT/'docs/quality-audit/real-world/evidence/relevance-labels.json',
 ROOT/'docs/quality-audit/index-growth/frozen/relevance-labels.json',
 ROOT/'docs/quality-audit/index-growth/controlled/relevance-labels.json',
 ROOT/'docs/quality-audit/index-growth/new-judgments.json',OUT/'new-judgments.json']:
    if file.exists(): labels.extend(load(file))
lookup={(r['case_id'],r['mode'],r['domain']):r for r in labels}
for variant in (sys.argv[2],):
    target=OUT/variant/'evidence'
    code=(ROOT/'tests/evaluations/bounded_cycle_benchmark.py').read_text(encoding='utf8')
    code=code[:code.index('known=load(SOURCE/')]
    code=code.replace("OUT=ROOT/'outputs/bounded-cycle'",f"OUT=Path({str(OUT)!r})")
    code=code.replace('variant=sys.argv[1]',f'variant={variant!r}')
    with contextlib.redirect_stdout(io.StringIO()):
        exec(compile(code,'v2-frozen-benchmark','exec'),{'__file__':str(ROOT/'tests/evaluations/bounded_cycle_benchmark.py')})
    runs=load(target/'replay-results.json');reviewed=[];pending=[]
    for c in runs:
        for ref in c['references']:
            if ref['stage']=='absent_from_index': ref['stage']='absent_from_eligible_supply'
        for rank,domain in enumerate(c['returned_domains'],1):
            key=c['case_id'],c['mode'],domain
            label=lookup.get(key)
            if label is None:
                label={'case_id':c['case_id'],'mode':c['mode'],'domain':domain,'label':None,'rationale':'Pending explicit product-evidence adjudication'}
                pending.append({**label,'rank':rank,'query':c['query']})
            reviewed.append({**label,'rank':rank})
    (target/'replay-results.json').write_text(json.dumps(runs,indent=2))
    (target/'relevance-labels.json').write_text(json.dumps(reviewed,indent=2))
    (OUT/variant/'pending.json').write_text(json.dumps(pending,indent=2))
    os.chdir(target.parent)
    with contextlib.redirect_stdout(io.StringIO()): runpy.run_path(str(ROOT/'docs/quality-audit/real-world/evidence/measure.py'))
    metrics=load(target/'benchmark-metrics.json')
    metrics.update(benchmark='Frozen endpoint; isolated V2 coverage experiment',unadjudicated_placements=len(pending))
    if pending: metrics['label_status']='Incomplete: new placements require explicit adjudication; rates are provisional'
    (target/'benchmark-metrics.json').write_text(json.dumps(metrics,indent=2))
    print(json.dumps({'variant':variant,'pending_judgments':len(pending),
        'errors':sum(v['all25']['errors'] for v in metrics['summary'].values())}))
