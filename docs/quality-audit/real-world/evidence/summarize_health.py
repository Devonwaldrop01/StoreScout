import json,pathlib,collections,urllib.parse,math
P=pathlib.Path('evidence');obs=collections.defaultdict(dict)
def add(o):
 obs[o['domain']][o['checked_at']]=o
 if o.get('previous_attempt'):add(o['previous_attempt'])
for dn in ['public-observations','supplemental-observations']:
 for f in (P/dn).glob('*.json'):add(json.loads(f.read_text()))
sample=json.loads((P/'health-sample.json').read_text());idx={r['domain']:r for r in json.loads((P/'index-snapshot.json').read_text())}
flags={};compact=[]
for domain,attempts in obs.items():
 aa=list(attempts.values())
 flags[domain]={k:any(a[k] for a in aa) for k in ['accessible_home','readable_nonempty_catalog','shopify_evidence','password_signal','parking_signal']}
 if domain=='aether.run':flags[domain]['parking_signal']=True  # analyst-confirmed domain-broker redirect, retained source URL
 flags[domain]['unknown_access']=not(flags[domain]['accessible_home'] or flags[domain]['readable_nonempty_catalog'])
 flags[domain]['http_402_unavailable']=any(x.get('status')==402 for a in aa for x in a['checks'].values())
 flags[domain]['challenge_observed']=any(x.get('challenge_signal') for a in aa for x in a['checks'].values())
 flags[domain]['public_catalog_empty']=any(x.get('readable_catalog') and not x.get('products') for a in aa for x in a['checks'].values())
 facts=[]
 for a in sorted(aa,key=lambda x:x['checked_at']):
  checks={}
  for kind,x in a['checks'].items():
   c={k:v for k,v in x.items() if k not in ('text','products')}
   c['observed_product_count']=len(x['products']) if 'products' in x else None
   c['product_examples']=[{'title':p['title'],'product_type':p['product_type'],'handle':p['handle']} for p in x.get('products',[])[:10]]
   checks[kind]=c
  facts.append({'checked_at':a['checked_at'],'checks':checks})
 compact.append({'domain':domain,'flags':flags[domain],'observations':facts})
out={'sample_n':len(sample),'strata_n':len({tuple(s['stratum']) for s in sample}),'observation_domains':len(obs),'metrics':{},'by_status':{},'strata':[]}
N=sum(s['weight'] for s in sample)
for key in next(iter(flags.values())):
 n=sum(flags[s['domain']][key] for s in sample);estimate=sum(s['weight']*flags[s['domain']][key] for s in sample)/N
 # Conservative concentration bound under stratified simple-random sampling;
 # deterministic hash ordering implements a reproducible pseudo-random design.
 margin=math.sqrt(math.log(40)/2*sum((s['weight']/N)**2 for s in sample))
 out['metrics'][key]={'observed_sample_count':n,'weighted_rate':estimate,'weighted_estimated_rows':estimate*N,'conservative_95_bound':[max(0,estimate-margin),min(1,estimate+margin)],'margin':margin}
for status in sorted({s['stratum'][1] for s in sample}):
 ss=[s for s in sample if s['stratum'][1]==status];den=sum(s['weight'] for s in ss)
 out['by_status'][status]={'sample_n':len(ss),'population_n':den,'readable_nonempty_catalog_n':sum(flags[s['domain']]['readable_nonempty_catalog'] for s in ss),'weighted_catalog_rate':sum(s['weight']*flags[s['domain']]['readable_nonempty_catalog'] for s in ss)/den}
for key in sorted({tuple(s['stratum']) for s in sample}):
 ss=[s for s in sample if tuple(s['stratum'])==key]
 out['strata'].append({'stratum':key,'population_n':ss[0]['N'],'n':len(ss),'catalog_successes':sum(flags[s['domain']]['readable_nonempty_catalog'] for s in ss),'unknown_access':sum(flags[s['domain']]['unknown_access'] for s in ss),'uncertainty':'single observation; no within-stratum variance estimate' if len(ss)==1 else 'small stratified sample; see overall conservative bound'})
out['confirmed_platform_absence']=None;out['confirmed_dead']=None;out['wholesale_only_rate']=None
out['interpretation']='These are observed access/evidence rates in a bounded public-check window, not sales activity, full-catalog completeness, or exhaustive platform absence. Unknown access is not dead. Confidence bounds address sample selection only, not probe or label errors.'
out['check_window']=[min(a['checked_at'] for dd in obs.values() for a in dd.values()),max(a['checked_at'] for dd in obs.values() for a in dd.values())]
(P/'public-health-summary.json').write_text(json.dumps(out,indent=2));(P/'public-evidence-compact.json').write_text(json.dumps(compact,indent=2))
print(json.dumps({k:v for k,v in out.items() if k!='strata'},indent=2))
for flag in ['password_signal','parking_signal','http_402_unavailable']:
 print(flag,[(s['domain'],s['stratum']) for s in sample if flags[s['domain']][flag]])
