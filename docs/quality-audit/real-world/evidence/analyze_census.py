import json,pathlib,collections,datetime,hashlib,re,urllib.parse
P=pathlib.Path('evidence');rows=json.loads((P/'index-snapshot.json').read_text());now=datetime.datetime.fromisoformat('2026-09-05T20:44:23.705755+00:00')
def age(s):
 if not s:return 'missing'
 d=(now-datetime.datetime.fromisoformat(s)).total_seconds()/86400
 return 'future' if d<0 else '0-7' if d<=7 else '8-30' if d<=30 else '31-60' if d<=60 else '>60'
fields=['category','subcategory','category_confidence','category_evidence','brand_name','description','product_titles','product_types','dna_keywords','target_customer','pricing_tier','median_price','country','language','collections','homepage_message','price_bands','knowledge_at','dna_at','last_verified_at']
out={'total':len(rows),'status':dict(collections.Counter(r['status'] for r in rows)),'groups':{}}
for name,subset in [('all',rows),('verified',[r for r in rows if r['status']=='verified'])]:
 out['groups'][name]={'n':len(subset),'category':dict(collections.Counter(r.get('category') or 'NULL' for r in subset)),'subcategory':dict(collections.Counter(r.get('subcategory') or 'NULL' for r in subset)),
 'ages':{f:dict(collections.Counter(age(r.get(f)) for r in subset)) for f in ['last_verified_at','knowledge_at','last_light_scanned_at','verified_at','dna_at','updated_at']},
 'missing':{f:sum(r.get(f) is None or r.get(f)=='' or r.get(f)==[] or r.get(f)=={} for r in subset) for f in fields},
 'confidence':dict(collections.Counter(str(r.get('category_confidence')) for r in subset)),
 'source':dict(collections.Counter(r.get('source') or 'NULL' for r in subset)),
 'classified_confident':sum(bool(r.get('category') and r['category']!='Other' and (r.get('category_confidence') or 0)>=55) for r in subset)}
norms=collections.defaultdict(list);brands=collections.defaultdict(list)
for r in rows:
 d=r['domain'].lower().strip();d=re.sub(r'^https?://','',d).split('/')[0];d=re.sub('^www[.]','',d).rstrip('.')
 norms[d].append(r['domain'])
 if r.get('brand_name'):brands[r['brand_name'].strip().lower()].append(r['domain'])
out['normalized_collisions']={d:v for d,v in norms.items() if len(v)>1}
out['same_brand_candidates']={d:v for d,v in brands.items() if len(v)>1}
out['failure_reasons']=dict(collections.Counter(r.get('failure_reason') or 'NULL' for r in rows if r['status'] in ('failed','rejected')))
out['wholesale_flag']=sum(r.get('sells_wholesale') is True for r in rows)
out['no_currency_column']=True
out['domain_timestamp_md5']=hashlib.md5('\n'.join(r['domain']+':'+(r.get('updated_at') or '').replace('T',' ').replace('+00:00','+00') for r in rows).encode()).hexdigest()
out['snapshot_sha256']=hashlib.sha256((P/'index-snapshot.json').read_bytes()).hexdigest()
(P/'census-analysis.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
