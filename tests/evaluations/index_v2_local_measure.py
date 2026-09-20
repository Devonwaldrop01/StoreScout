"""Local V2 persistence/child throughput using 36 already captured catalogs.

No verification requests, paid APIs or production writes. Observation timestamps
remain unchanged. A synthetic queue clock skips dispatch waits for CPU/I/O timing;
these timings are not merchant verification throughput. All classification children
use the real supervisor and isolated environment.
"""
from copy import deepcopy
from datetime import datetime,timezone,timedelta
import hashlib,json,platform,socket,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from index_v2.identity import prepare,canonical
from index_v2.store import Store
from index_v2.worker import process_job,execute_child
from index_v2.experiment import export


def main():
    source=ROOT.parent/'storescout-phase1/outputs/production-access/outcomes.json'
    raw=source.read_bytes();records=json.loads(raw)
    rows={canonical(r['verified_row']['domain']):deepcopy(r['verified_row']) for r in records if r['result'].get('outcome')=='verified'}
    for domain,row in rows.items(): row['domain']=domain
    def forbidden(*a,**k): raise AssertionError('No network in captured parent replay')
    socket.getaddrinfo=forbidden;socket.socket.connect=forbidden
    now=datetime.now(timezone.utc)
    m=prepare([{'domain':d,'source':'previous public catalog capture'} for d in rows],batch_size=len(rows),
        expires_at=(now+timedelta(days=7)).isoformat(),source_sha256=hashlib.sha256(raw).hexdigest())
    latencies=[]
    def captured(payload,renew,stop):
        if payload['stage']=='verify':
            return {'state':'verified_shopify','row':deepcopy(rows[payload['canonical']]),'requests':[],
                    'mode':'captured input; no fresh verification'}
        start=time.perf_counter();result=execute_child(payload,renew,stop)
        latencies.append(time.perf_counter()-start);return result
    with tempfile.TemporaryDirectory(prefix='storescout-v2-measure-') as folder:
        path=Path(folder)/'v2.sqlite';Store.initialize(path);clock=[now.timestamp()]
        db=Store(path,clock=lambda:clock[0]);key=db.seed(m)
        started=time.perf_counter()
        for _ in rows:
            process_job(db,db.claim(key),captured);clock[0]+=11
        elapsed=time.perf_counter()-started
        summary=db.summary();confidence=dict(db.db.execute('SELECT confidence,count(*) FROM store_classification_v2 GROUP BY confidence'))
        before=summary.copy();db.close();db=Store(path,clock=lambda:clock[0]);db.seed(m)
        assert db.summary()==before and db.claim(key) is None
        out=ROOT/'outputs/index-v2-tool-validation'/now.strftime('%Y%m%dT%H%M%S')
        sets=export(db,out,now=now)
        db.backup(Path(folder)/'backup.sqlite')
        report={'kind':'Captured catalog + real isolated classification child + SQLite, not live verification',
            'timestamp':now.isoformat(),'platform':platform.platform(),'python':platform.python_version(),
            'source_sha256':hashlib.sha256(raw).hexdigest(),'captured_verified':len(rows),**summary,
            'confidence_distribution':confidence,'wall_seconds':elapsed,
            'classification_child_mean_seconds':sum(latencies)/len(latencies),'classification_child_max_seconds':max(latencies),
            'rows_per_second_including_durable_writes':len(rows)/elapsed,'exports':{k:len(v) for k,v in sets.items()},
            'experiment_directory':str(out.relative_to(ROOT)),
            'restart_idempotency':'passed; no new attempts','network_requests':0,'paid_ai_calls':0,
            'limitations':['Windows measurement; Linux image gate pending','Input sample selected successful captures',
                'No fresh reachability/yield measurement','Dispatch pacing skipped with injected test clock',
                'Observation timestamps retained; no manufactured freshness']}
        db.close()
    target=ROOT/'docs/quality-audit/index-v2/local-measurement.json'
    target.write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps(report,indent=2))


if __name__=='__main__': main()
