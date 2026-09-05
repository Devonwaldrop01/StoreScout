import json,pathlib,collections
P=pathlib.Path('evidence');sample=[s for s in json.loads((P/'health-sample.json').read_text()) if s['stratum'][1]=='verified'];idx={r['domain']:r for r in json.loads((P/'index-snapshot.json').read_text())}
review={}
def mark(status,domains,reason):
 for d in domains.split():review[d]=(status,reason)
mark('wrong','fashionnova.com','Observed fashion apparel; stored Jewelry/Watches does not describe the main assortment.')
mark('wrong','spigen.com','Observed device cases/accessories; stored Jewelry/Watches does not describe the main assortment.')
mark('wrong','kinugawaturbo.com','Observed turbocharger/compressor automotive parts contradict stored Kids & Baby/Toys.')
mark('wrong','benchmarkabrasives.com','Observed industrial abrasives contradict stored Outdoors/Water Sports.')
mark('unclassified','fedfitness.com shoplinenlace.com moft.us','Stored Other/General is not a useful specific business classification; public offerings support a more specific class.')
mark('unknown','glitzpuffs.com mujjo.com','Current unavailable/redirect-limit observation does not support independent category adjudication.')
mark('partial','undisputedbelts.com wetplants.com','Broad classification has a plausible adjacency but championship awards/aquatic plants do not cleanly fit the stored apparel-accessory/home-decor niche.')
reviews=[]
for s in sample:
 d=s['domain'];r=idx[d];status,reason=review.get(d,('correct','Current official homepage/catalog supports the stored broad category; this does not validate every subcategory or product.'))
 sub='not separately scored'
 if d=='thephotostick.com':sub='wrong: storage/photo backup hardware is not wearable technology'
 if d=='inspiredgo.ca':sub='partial/wrong: prepared meals and salads, not primarily snacks'
 reviews.append({**s,'category':r['category'],'subcategory':r['subcategory'],'confidence':r.get('category_confidence'),'broad_category_review':status,'reason':reason,'subcategory_review':sub,'evidence_url':'https://'+d})
out={'sample_n':len(reviews),'raw_counts':dict(collections.Counter(r['broad_category_review'] for r in reviews)),'weighted_rates':{status:sum(r['weight'] for r in reviews if r['broad_category_review']==status)/426 for status in ['correct','partial','wrong','unclassified','unknown']},'reviews':reviews,'limitation':'Single analyst, stratified small sample with many singleton strata. Heuristic confidence is not calibrated probability; no precise per-confidence calibration curve or full confusion matrix is justified.'}
(P/'classification-review.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k!='reviews'},indent=2))
print([(r['domain'],r['confidence']) for r in reviews if r['broad_category_review']=='wrong'])
