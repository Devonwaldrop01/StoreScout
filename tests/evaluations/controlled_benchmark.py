"""Run preserved endpoint replay on independently rebuilt local SQL captures.
Never assigns old rank labels to newly returned merchants.
"""
import asyncio
import json
import os
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'docs/quality-audit/real-world/evidence'
OUT=ROOT/'outputs/controlled-validation'
variant=sys.argv[1]
target=OUT/variant
load=lambda p:json.loads(p.read_text(encoding='utf8'))
for name in ('replay-plan.json',): shutil.copy2(SOURCE/name,target/'evidence'/name)
metadata=OUT/'run-metadata.json'
clock=load(metadata)['finished_at'] if metadata.exists() else '2026-09-05T20:44:23.705755+00:00'
os.chdir(target)
loop=asyncio.new_event_loop()
asyncio.run=lambda coro:loop.run_until_complete(coro)
text=(SOURCE/'replay.py').read_text(encoding='utf8').replace('2026-09-05T20:44:23.705755+00:00',clock)
exec(compile(text,str(SOURCE/'replay.py'),'exec'),{'__file__':str(SOURCE/'replay.py')})
loop.close()
runs=load(target/'evidence/replay-results.json')
old=load(SOURCE/'replay-results.json')
old_labels=load(SOURCE/'relevance-labels.json')
lookup={(r['case_id'],r['mode'],r['domain']):r for r in old_labels}
labels=[]; pending=[]
for case in runs:
 for rank,domain in enumerate(case['returned_domains'],1):
  key=(case['case_id'],case['mode'],domain)
  if key in lookup:
   labels.append({**lookup[key],'rank':rank,'label_provenance':'frozen merchant/case/mode label, remapped by identity'})
  else:
   pending.append({'case_id':case['case_id'],'mode':case['mode'],'rank':rank,'domain':domain,'query':case['query']})
(target/'pending-adjudications.json').write_text(json.dumps(pending,indent=2),encoding='utf8')
(target/'reused-labels.json').write_text(json.dumps(labels,indent=2),encoding='utf8')
parity=sum(a['returned_domains']==b['returned_domains'] and a['error']==b['error'] for a,b in zip(old,runs))
if variant=='before':
 assert parity==50 and not pending, 'Rebuilt baseline must reproduce every original case before measuring change'
print('PARITY',parity,'/50; new placements',len(pending))
