import json,pathlib,collections,csv
P=pathlib.Path('evidence');runs=json.loads((P/'replay-results.json').read_text());labels=json.loads((P/'relevance-labels.json').read_text());bycase=collections.defaultdict(list)
for l in labels:bycase[(l['case_id'],l['mode'])].append(l)
cases=[]
for c in runs:
 ll=sorted(bycase[(c['case_id'],c['mode'])],key=lambda x:x['rank'])
 count=lambda pred,top=None:sum(pred(l['label']) for l in (ll if top is None else ll[:top]))
 useful=lambda l:l is not None and l>=2
 m={'returned':len(ll),'useful':count(useful),'strong':count(lambda l:l==3),'wrong':count(lambda l:l==0),'unknown':count(lambda l:l is None),'precision_at_5':count(useful,5)/5,'precision_at_10':count(useful,10)/10,'precision_at_8':count(useful,8)/8,'strong_precision_at_5':count(lambda l:l==3,5)/5,'three_useful_top5':count(useful,5)>=3,'wrong_top5':count(lambda l:l==0,5)>0,'known_reference_hits':sum(r['stage']=='returned' for r in c['references']),'known_reference_total':len(c['references']),'known_reference_recall':sum(r['stage']=='returned' for r in c['references'])/len(c['references']), 'error':c['error']}
 cases.append({**{k:c[k] for k in ['case_id','business','mode','niche','role','query']},'metrics':m,'labels':ll,'references':c['references']})
def aggregate(cs):
 n=len(cs);total=sum(c['metrics']['returned'] for c in cs)
 s=lambda k:sum(c['metrics'][k] for c in cs)
 return {'cases':n,'returned':total,'useful':s('useful'),'wrong':s('wrong'),'unknown':s('unknown'),'precision_at_5':s('precision_at_5')/n,'precision_at_10':s('precision_at_10')/n,'strong_precision_at_5':s('strong_precision_at_5')/n,'useful_result_rate':s('useful')/total if total else None,'obviously_wrong_rate':s('wrong')/total if total else None,'unknown_rate':s('unknown')/total if total else None,'three_useful_searches':s('three_useful_top5'),'three_useful_rate':s('three_useful_top5')/n,'wrong_top5_search_rate':s('wrong_top5')/n,'known_reference_recall':s('known_reference_hits')/s('known_reference_total'),'known_reference_hits':s('known_reference_hits'),'known_reference_total':s('known_reference_total'),'errors':sum(bool(c['metrics']['error']) for c in cs),'reference_stages':dict(collections.Counter(r['stage'] for c in cs for r in c['references']))}
summary={}
for mode in ['description_only','structured_profile']:
 cc=[c for c in cases if c['mode']==mode];core=[c for c in cc if c['role']=='core'];by_niche={n:aggregate([c for c in core if c['niche']==n]) for n in sorted({c['niche'] for c in core})}
 summary[mode]={'all25':aggregate(cc),'core24':aggregate(core),'control':aggregate([c for c in cc if c['role']!='core']),'core_by_niche':by_niche,'family_macro_p5':sum(x['precision_at_5'] for x in by_niche.values())/len(by_niche)}
out={'summary':summary,'cases':cases,'label_status':'single-analyst evidence-adjudicated, not an independent blind human panel','benchmark':'ff555bb local index-only at frozen initial census clock, defaults minimum=60/category_floor=55; production environment overrides and paid AI behavior unmeasured'}
(P/'benchmark-metrics.json').write_text(json.dumps(out,indent=2))
with (P/'case-metrics.csv').open('w',newline='') as f:
 cols=['case_id','business','mode','niche','role','returned','precision_at_5','precision_at_10','known_reference_recall','useful','wrong','unknown','three_useful_top5'];w=csv.DictWriter(f,fieldnames=cols);w.writeheader()
 for c in cases:w.writerow({k:({**c,**c['metrics']}).get(k) for k in cols})
print(json.dumps(summary,indent=2))
