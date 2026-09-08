"""Replay unchanged bounded-cycle captures into a NEW output directory."""
import json,runpy,shutil,sys,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
variant=sys.argv[1]
OUT=ROOT/'outputs/production-access/benchmark'
target=OUT/variant/'evidence';target.mkdir(parents=True,exist_ok=True)
source=ROOT/'outputs/bounded-cycle'
for name in ['index-snapshot.json','retrieval-postgres.json']:
    shutil.copy2(source/variant/'evidence'/name,target/name)
shutil.copy2(source/'clock.json',OUT/'clock.json')
code=(ROOT/'tests/evaluations/bounded_cycle_benchmark.py').read_text(encoding='utf8')
code=code.replace("OUT=ROOT/'outputs/bounded-cycle'", "OUT=ROOT/'outputs/production-access/benchmark'")
exec(compile(code,'bounded_cycle_benchmark.py','exec'),{'__file__':str(ROOT/'tests/evaluations/bounded_cycle_benchmark.py')})
load=lambda p:json.loads(p.read_text(encoding='utf8'))
old=load(source/variant/'evidence/replay-results.json')
new=load(target/'replay-results.json')
assert len(old)==len(new)==50
for a,b in zip(old,new):
    assert (a['case_id'],a['mode'],a['returned_domains'])==(b['case_id'],b['mode'],b['returned_domains'])
shutil.copy2(source/variant/'evidence/relevance-labels.json',target/'relevance-labels.json')
os.chdir(target.parent)
runpy.run_path(str(ROOT/'docs/quality-audit/real-world/evidence/measure.py'))
metrics=load(target/'benchmark-metrics.json')
for mode in ['description_only','structured_profile']:
    assert metrics['summary'][mode]['core24']['errors']==0
print('Preserved 50/50 ranked result lists; empty searches no longer error.')
