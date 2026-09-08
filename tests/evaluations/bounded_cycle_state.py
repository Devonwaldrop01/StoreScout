"""Offline reapplication to the same measured raw successes; no new acquisition."""
import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parent))
import controlled_catalog_validation as h
from app.services.discovery_quality import is_recent_verified,is_classification_usable
from test_verification_lifecycle import MemoryDB
OUT=h.ROOT/'outputs/bounded-cycle'; OUT.mkdir(parents=True,exist_ok=True)
meta=h.load(h.OUT/'run-metadata.json'); clock=datetime.fromisoformat(meta['finished_at'])
class FrozenDate(datetime):
    @classmethod
    def now(cls,tz=None): return clock
h.index.datetime=FrozenDate
import app.services.discovery_quality as quality
quality.datetime=FrozenDate
h.index._get=h.deny
records=h.load(h.OUT/'outcomes.json'); rows=h.load(h.SOURCE/'index-snapshot.json')
db=MemoryDB(rows); prior={r['domain']:r for r in rows}; results=[]
class_keys={'category','subcategory','category_confidence','category_evidence','knowledge_at','description','store_dna',
    'dna_keywords','dna_signature','dna_at','target_customer','brand_keywords'}
for r in records:
    d=r['domain']
    if r['result']['outcome']!='verified':
        db.rows[d]=deepcopy(r['after_row']); continue
    fields={k:v for k,v in r['verified_row'].items() if k not in class_keys}
    # The captured raw validator already established this observation; verify
    # its signature again and carry the original byte-backed fields forward.
    req=next(q for q in r['requests'] if '/products.json?' in q['url'])
    products=json.loads((h.OUT/'raw'/req['body_file']).read_bytes())['products']
    assert h.index.lifecycle.successful_catalog(products,clock,'replay')['signature']==fields['catalog_observation']['signature']
    fields.update(h.index.classification_transition(prior[d],fields))
    db.rows[d].update(fields)
    transition=deepcopy(db.rows[d])
    classification=h.index.run_knowledge(db,deepcopy(db.rows[d]))
    results.append({'domain':d,'before':r['classification'],'replacement':classification,
        'transition_state':transition['catalog_observation'].get('classification_state'),
        'transition_usable':is_classification_usable(transition,now=clock),
        'after_usable':is_recent_verified(db.rows[d],now=clock) and is_classification_usable(db.rows[d],now=clock),
        'after_row':db.rows[d]})
h.save(OUT/'index-after.json',list(db.rows.values()))
h.save(OUT/'classification-results.json',results)
h.save(OUT/'clock.json',{'clock':clock.isoformat()})
print('Replacement pass',sum(r['replacement']['confidence']>=55 for r in results),'/',len(results))
print('Usable after',sum(r['after_usable'] for r in results))
print('Full usable supply',sum(is_recent_verified(r,now=clock) and is_classification_usable(r,now=clock) for r in db.rows.values()))
