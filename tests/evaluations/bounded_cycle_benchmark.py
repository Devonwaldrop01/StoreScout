"""Preserved benchmark endpoint, adapting only DB capture support to fixed JSONB query."""
import asyncio,json,os,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; SOURCE=ROOT/'docs/quality-audit/real-world/evidence'
OUT=ROOT/'outputs/bounded-cycle'; variant=sys.argv[1]; target=OUT/variant
load=lambda p:json.loads(p.read_text(encoding='utf8'))
clock=load(OUT/'clock.json')['clock']
shutil.copy2(SOURCE/'replay-plan.json',target/'evidence/replay-plan.json')
text=(SOURCE/'replay.py').read_text(encoding='utf8').replace('2026-09-05T20:44:23.705755+00:00',clock)
text=text.replace("channel='category' if", "channel='dna' if any(op[0]=='or_' and op[1][0].startswith('dna_keywords.cs.') for op in self.ops) else 'category' if")
text=text.replace("if op=='or_':assert", "if op=='or_' and channel!='dna':assert")
text=text.replace("data=[{k:copy.deepcopy(by_domain[d].get(k)) for k in cols} for d in c['domains'] or []]", "data=[copy.deepcopy(by_domain[d]) if self.columns=='*' else {k:copy.deepcopy(by_domain[d].get(k)) for k in cols} for d in c['domains'] or []]")
text=text.replace("if not m['matched_terms']:reasons.append('no_matched_product_terms')", "if not m['matched_terms']:reasons.append('no_matched_product_terms')\n        if not m['intent']['supported']:reasons.append('product_intent_mismatch')\n        if not quality.is_classification_usable(r,now=clock):reasons.append('classification_lifecycle_gate')")
os.chdir(target);loop=asyncio.new_event_loop();asyncio.run=lambda coro:loop.run_until_complete(coro)
exec(compile(text,str(SOURCE/'replay.py'),'exec'),{'__file__':str(SOURCE/'replay.py')});loop.close()
runs=load(target/'evidence/replay-results.json')
plans={p['id']:p for p in load(SOURCE/'replay-plan.json')}
for r in runs:
 assert r['user_category']==plans[r['case_id']]['user_category'], 'Query-only classification must remain unchanged'
 assert {t['channel'] for t in r['retrieval']}==({'category','lexical','dna'} if r['user_category'] else {'lexical','dna'}), 'A retrieval channel failed silently'
known=load(SOURCE/'relevance-labels.json')+load(ROOT/'outputs/controlled-validation/after/evidence/relevance-labels.json')
lookup={(r['case_id'],r['mode'],r['domain']):r for r in known}
labels=[];pending=[]
for c in runs:
 for rank,d in enumerate(c['returned_domains'],1):
  key=c['case_id'],c['mode'],d
  if key in lookup: labels.append({**lookup[key],'rank':rank})
  else:pending.append({'case_id':c['case_id'],'mode':c['mode'],'domain':d,'rank':rank,'query':c['query']})
(target/'known-labels.json').write_text(json.dumps(labels,indent=2),encoding='utf8')
(target/'pending.json').write_text(json.dumps(pending,indent=2),encoding='utf8')
print('New placements requiring review:',len(pending))
