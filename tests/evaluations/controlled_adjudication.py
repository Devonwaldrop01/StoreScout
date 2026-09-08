"""Explicit analyst decisions for this validation; never used in application ranking."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import runpy
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'outputs/controlled-validation'
SOURCE=ROOT/'docs/quality-audit/real-world/evidence'
load=lambda p:json.loads(p.read_text(encoding='utf8'))
clock=load(OUT/'run-metadata.json')['finished_at']
reviewed_at=datetime.now(timezone.utc).isoformat()
# Each decision follows examination of raw samples or the preserved public
# observation, with direct merchant pages checked for the five newly exposed
# merchants lacking prior public observations. No labels inferred from rank.
decisions={
 'babysprouts.com':(0,'Raw catalog contains children’s dresses, skirts and rompers. Cosmetic-looking color words do not establish tinted sunscreen or complexion makeup.'),
 'dear-paw.com':(0,'Recorded public catalog is cat toys and cat tunnels. Species and use contradict edible freeze-dried dog treats.'),
 'furrybodypillows.com':(0,'Merchant collections sell artist-designed body-pillow covers. Canine illustrations are not edible dog treats.'),
 'shop.phoenixseattle.com':(0,'Merchant catalog/navigation offers comics, graphic novels, cards and game events, not raw dog treats.'),
 'epicreads.com':(0,'Merchant homepage and catalog sell novels and book editions. No hiking backpack or shelter substitution.'),
 'beachinsurf.com.au':(1,'Surf hardware, wetsuits and general backpacks are adjacent outdoor goods; lightweight hiking packs or shelters are not established.'),
 'chiquel.com':(0,'Public storefront identifies wigs and hairpieces. Neither sensitive baby skincare nor fragrance-free infant formulations are evidenced.'),
 'cheesebros.com':(0,'Public catalog contains cheese, curds and gift boxes. A cheese subscription is not specialty coffee.'),
 'exoticsnackguysshop.com':(0,'Merchant catalog sells imported chips, sweets and soft drinks. No specialty coffee or home-roasting subscription substitute is evidenced.'),
 'tasteofbritain.com':(1,'Broad British groceries, tea and giftware are adjacent food retail. Specialty coffee bean subscriptions are not demonstrated.'),
 'lheureuxinc.com':(2,'Merchant offers whole-bean Ursae Éclipse with a subscribe-and-save delivery option. This is real recurring coffee supply; equipment-led retail and Canadian delivery make it a partial competitor.'),
 'corkcicle.com':(1,'Insulated cups and coffee mugs serve the coffee audience but do not replace freshly roasted coffee subscriptions.'),
 'www.theoriginalera.com':(0,'Raw catalog mixes adult graphic tees, bikes, skates and other goods. Children’s bamboo pajamas are not evidenced; generic clothing/kids words are insufficient.'),
 'muttluks.com':(1,'Public products are dog boots, harnesses and paw care. Same dog-owner audience, without edible freeze-dried treat substitution.'),
 'thebizzbybabs.com':(0,'Merchant storefront sells intimacy and personal-care goods, not mechanical keyboards.'),
}
urls={
 'epicreads.com':['https://epicreads.com/'],
 'shop.phoenixseattle.com':['https://shop.phoenixseattle.com/'],
 'exoticsnackguysshop.com':['https://exoticsnackguysshop.com/'],
 'furrybodypillows.com':['https://furrybodypillows.com/collections'],
 'lheureuxinc.com':['https://lheureuxinc.com/en/products/ursae-eclipse'],
}
old={(c['case_id'],c['mode']):c for c in load(SOURCE/'replay-results.json')}
all_reviews=[]
for variant in ('before','after','sample_only','successes_only'):
 target=OUT/variant
 labels=load(target/'reused-labels.json')
 for p in load(target/'pending-adjudications.json'):
  d=p['domain']
  if d=='www.bambibaby.com':
   if p['case_id']=='epomaker':
    value,reason=0,'Raw catalog sells strollers, car seats, nursery furniture and crib linens. No mechanical keyboards; low-profile/models wording is incidental.'
   elif p['case_id']=='kytebaby':
    value,reason=1,'Nursery products, swaddles and crib bedding share an infant audience; bamboo sleep bags and sleepwear substitution is not established by the captured catalog.'
   else:
    value,reason=1,'Crib sheets and nursery quilts are adjacent bedding. Adult linen/bath collections or a broad adult home-and-apparel substitute are not established.'
  else: value,reason=decisions[d]
  labels.append({**p,'label':value,'rationale':reason,'checked_at':reviewed_at,
    'public_urls':urls.get(d,[f'https://{d}/',f'https://{d}/products.json?limit=250']),
    'label_provenance':'explicit controlled-validation analyst adjudication',
    'reviewer':'single analyst; not an independent blind human panel','access_unknown':False})
 runs=load(target/'evidence/replay-results.json')
 expected={(c['case_id'],c['mode'],d,i) for c in runs for i,d in enumerate(c['returned_domains'],1)}
 assert {(r['case_id'],r['mode'],r['domain'],r['rank']) for r in labels}==expected
 assert len(labels)==len(expected)
 (target/'evidence/relevance-labels.json').write_text(json.dumps(labels,indent=2),encoding='utf8')
 lookup={(r['case_id'],r['mode'],r['domain']):r for r in labels}
 for c in runs:
  previous=old[(c['case_id'],c['mode'])]['returned_domains']
  for rank,d in enumerate(c['returned_domains'],1):
   if d not in previous or (rank<=5 and d not in previous[:5]):
    all_reviews.append({'variant':variant,**lookup[(c['case_id'],c['mode'],d)],
      'entry_reviewed_at':reviewed_at,
      'entry_review_status':'Analyst reviewed product evidence and retained the recorded case-specific decision',
      'previous_rank':previous.index(d)+1 if d in previous else None,
      'entry_type':'new_top5' if rank<=5 else 'new_top10'})
 os.chdir(target)
 runpy.run_path(str(SOURCE/'measure.py'))
 metrics=load(target/'evidence/benchmark-metrics.json')
 metrics['benchmark']='Unchanged Phase 1 application discovery, rebuilt local PostgreSQL captures, paid AI disabled, at '+clock
 (target/'evidence/benchmark-metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf8')
(OUT/'entry-adjudications.json').write_text(json.dumps(all_reviews,indent=2),encoding='utf8')
print('All new top-five/top-ten entries adjudicated:',len(all_reviews))
