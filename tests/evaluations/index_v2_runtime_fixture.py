"""Synthetic, network-disabled container restart fixture; never a pilot input."""
from datetime import datetime,timezone,timedelta
import json
from pathlib import Path
import sys
import time

sys.path.insert(0,'/app')
from index_v2.identity import prepare
from index_v2.store import Store

root=Path('/var/data');path=root/'store-index-v2.sqlite'
if sys.argv[1]=='prepare':
    # Import only the synthetic test fixture in this setup process, not the worker.
    sys.path.insert(0,'/app/tests')
    from test_index_v2 import catalog
    manifest=prepare([{'domain':'example.com'}],batch_size=1,
        expires_at=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat(),
        source_sha256='a'*64)
    Store.initialize(path)
    store=Store(path,clock=lambda:time.time()-200)
    try:
        key=store.seed(manifest);job=store.claim(key)
        store.transition(job,'verifying');store.verified(job,catalog(),{})
        (root/'batch').write_text(key)
    finally: store.close()
elif sys.argv[1]=='check':
    store=Store(path)
    try:
        assert store.db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert store.db.execute('PRAGMA journal_mode').fetchone()[0]=='wal'
        summary=store.summary()
        assert summary['eligible']==summary['classification_saved']==summary['attempts']==1
        assert store.rows(eligible_only=True)[0]['category_confidence']==90
        assert store.db.execute('SELECT count(*) FROM jobs_v2 WHERE owner IS NOT NULL').fetchone()[0]==0
        assert store.db.execute('SELECT stopped_reason FROM batches').fetchone()[0] is None
        # Exact stable durable rows: a restart may not duplicate/overwrite results.
        snapshot={table:[list(row) for row in store.db.execute('SELECT * FROM '+table)] for table in
            ('jobs_v2','store_index_v2','store_verification_v2','store_classification_v2','events_v2')}
        saved=root/'snapshot.json'
        if saved.exists(): assert json.loads(saved.read_text())==snapshot
        else:
            saved.write_text(json.dumps(snapshot,sort_keys=True))
            store.backup(root/'backup.sqlite')
        backup=Store(root/'backup.sqlite')
        try: assert backup.summary()==summary
        finally: backup.close()
        print(json.dumps({'summary':summary,'metrics':store.metrics(),'integrity':'ok','restart_rows_unchanged':True}))
    finally: store.close()
else: raise ValueError('Unknown fixture action')
