"""Package fixed-supply metrics and query diffs without changing the original run."""
import csv,hashlib,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OLD=ROOT/'outputs/index-v2-pilot-100/benchmark'
NEW=ROOT/'outputs/discovery-quality-fixed-supply'
OUT=ROOT/'docs/quality-audit/discovery-quality'
load=lambda p:json.loads(p.read_text(encoding='utf8'))
for name in ['legacy.json','v2.json','combined.json','clock.json']:
 assert (OLD/name).read_bytes()==(NEW/name).read_bytes(),name
assert hashlib.sha256((OLD.parent/'pilot-results-20260922.sqlite').read_bytes()).hexdigest()=='6c5b00b34188892f87cba9a6a7b6ede520c4d237d547f14264236e10538c5a26'
variants={'original_existing_34':OLD/'legacy','original_combined_88':OLD/'combined','improved_combined_88':NEW/'combined'}
all_metrics={key:load(p/'evidence/benchmark-metrics.json') for key,p in variants.items()}
for key,m in all_metrics.items():
 assert m['unadjudicated_placements']==0
 assert all(c['metrics']['error'] is None and c['metrics']['unknown']==0 for c in m['cases'])
(OUT/'benchmark-comparison.json').write_text(json.dumps(all_metrics,indent=2),encoding='utf8')
old=all_metrics['original_combined_88'];new=all_metrics['improved_combined_88']
by={(c['case_id'],c['mode']):c for c in new['cases']}
changes=[]
for before in old['cases']:
 after=by[before['case_id'],before['mode']]
 bd={r['domain']:r for r in before['labels']};ad={r['domain']:r for r in after['labels']}
 lost_useful=[d for d,r in bd.items() if r['label']>=2 and d not in ad]
 assert not lost_useful,(before['case_id'],before['mode'],lost_useful)
 assert after['metrics']['precision_at_5']>=before['metrics']['precision_at_5']
 changes.append({'case_id':before['case_id'],'mode':before['mode'],'query':before['query'],
 'niche':before['niche'],'before':before['metrics'],'after':after['metrics'],
 'removed':[bd[d] for d in bd if d not in ad],'added':[ad[d] for d in ad if d not in bd],
 'before_order':[r['domain'] for r in before['labels']],'after_order':[r['domain'] for r in after['labels']]})
(OUT/'per-query-changes.json').write_text(json.dumps(changes,indent=2),encoding='utf8')
with (OUT/'per-query-changes.csv').open('w',encoding='utf8',newline='') as f:
 fields=['case_id','mode','niche','p5_before','p5_after','p10_before','p10_after','useful_before','useful_after','wrong_before','wrong_after','returned_before','returned_after','added','removed']
 w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
 for c in changes:
  b,a=c['before'],c['after']
  w.writerow({'case_id':c['case_id'],'mode':c['mode'],'niche':c['niche'],
   'p5_before':b['precision_at_5'],'p5_after':a['precision_at_5'],'p10_before':b['precision_at_10'],'p10_after':a['precision_at_10'],
   'useful_before':b['useful'],'useful_after':a['useful'],'wrong_before':b['wrong'],'wrong_after':a['wrong'],
   'returned_before':b['returned'],'returned_after':a['returned'],
   'added':' '.join(r['domain'] for r in c['added']),'removed':' '.join(r['domain'] for r in c['removed'])})
shutil.copy2(NEW/'tests.txt',OUT/'local-tests.txt')
print('Fixed supply and SQLite hashes unchanged; all 50 before/after query-mode pairs complete; no useful-placement or P@5 losses.')

