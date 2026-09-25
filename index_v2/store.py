"""Durable local queue; SQLite transactions own leases, budgets and results.

Only this process writes the V2 file. Public-fetch children have no DB handle.
No SQL names/URLs are accepted from merchant inputs.
"""
from contextlib import contextmanager,closing
from datetime import datetime,timezone
import json
from pathlib import Path
import sqlite3
import time
import uuid
from .identity import digest, encoded, validate


class LostLease(RuntimeError): pass


class Store:
    def __init__(self,path, *, clock=time.time,canary=None):
        self.canary=canary
        self.path=Path(path); self.clock=clock
        self.db=sqlite3.connect(self.path,timeout=5,isolation_level=None)
        self.db.row_factory=sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=FULL')
        version=self.db.execute('PRAGMA user_version').fetchone()[0]
        if version!=1:
            self.db.close()
            raise ValueError('V2 schema not initialized or unsupported; use explicit init')

    @staticmethod
    def initialize(path):
        path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
        if path.exists(): raise FileExistsError('Refuse to migrate/replace an existing database')
        with closing(sqlite3.connect(path)) as db:
            db.executescript(Path(__file__).with_name('001_initial.sql').read_text())

    def close(self): self.db.close()

    @contextmanager
    def transaction(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.db.execute('COMMIT')
        except BaseException:
            self.db.execute('ROLLBACK');raise

    def seed(self,manifest):
        validate(manifest);key=digest(manifest);now=self.clock()
        with self.transaction():
            self.db.execute('INSERT OR IGNORE INTO batches VALUES (?,?,NULL,?)',(key,encoded(manifest),now))
            for e in manifest['entries']:
                self.db.execute('INSERT OR IGNORE INTO store_index_v2(canonical,fetch_host,updated_at) VALUES (?,?,?)',
                                (e['canonical'],e['fetch_host'],now))
                self.db.execute("INSERT OR IGNORE INTO jobs_v2(canonical,batch,state) VALUES (?,?,'pending')",(e['canonical'],key))
                for p in e['provenance']:
                    self.db.execute('INSERT OR IGNORE INTO provenance_v2 VALUES (?,?,?,?)',
                                    (key,e['canonical'],p['hostname'],encoded(p)))
        return key

    def manifest(self,key):
        row=self.db.execute('SELECT * FROM batches WHERE digest=?',(key,)).fetchone()
        if not row: raise ValueError('Unknown batch')
        return json.loads(row['manifest'])

    def event(self,attempt,state):
        self.db.execute('INSERT INTO events_v2(attempt_id,state,at) VALUES (?,?,?)',(attempt,state,self.clock()))

    def _owned(self,job):
        row=self.db.execute('SELECT * FROM jobs_v2 WHERE canonical=?',(job['canonical'],)).fetchone()
        if not row or row['owner']!=job['owner'] or row['attempt_id']!=job['attempt_id'] or (row['lease_until'] or 0)<=self.clock():
            raise LostLease('Owner absent, expired or superseded')
        return row

    def pause(self,key,reason):
        if self.canary:
            from .canary import marker
            if not self.canary_stopped(): self.event(marker(self.canary),'stopped_'+reason)
            return
        self.db.execute('UPDATE batches SET stopped_reason=? WHERE digest=?',(reason,key))

    def canary_stopped(self):
        from .canary import stopped
        return stopped(self)

    def record_protection(self,job,events):
        from .protection import enrich
        with self.transaction():
            self._owned(job)
            data=json.loads(self.db.execute('SELECT result_json FROM store_verification_v2 WHERE attempt_id=?',(job['attempt_id'],)).fetchone()[0] or '{}')
            records=enrich(events,job,None)
            old=data.get('protection_events',[])
            if records[:len(old)]!=old: raise ValueError('Protection evidence changed')
            data['protection_events']=records
            self.db.execute('UPDATE store_verification_v2 SET result_json=? WHERE attempt_id=?',(encoded(data),job['attempt_id']))
            if self.canary and records: self.pause(job['batch'],'first_protection_event')

    def with_protection(self,job,result,succeeded=None):
        data=json.loads(self.db.execute('SELECT result_json FROM store_verification_v2 WHERE attempt_id=?',(job['attempt_id'],)).fetchone()[0] or '{}')
        records=data.get('protection_events',[])
        if records:
            result=dict(result,protection_events=[dict(e,verification_succeeded=succeeded) for e in records])
        return result

    def hold_verified(self,job):
        with self.transaction():
            self._owned(job)
            self.db.execute("UPDATE jobs_v2 SET owner=NULL,lease_until=NULL WHERE canonical=? AND state='verified'",(job['canonical'],))
            self.event(job['attempt_id'],'verified_checkpoint_held_protection')

    def recover_expired_attempt(self,key,attempt):
        """Explicit paused-batch reconciliation only; never enables or claims work.

        Caller must first establish that the old supervisor/child are gone.
        Exact attempt identity, pause and expired lease are transactional guards.
        """
        from .compute import retry_time
        with self.transaction():
            if self.db.execute("SELECT 1 FROM events_v2 WHERE attempt_id=? AND state='expired_attempt_reconciled'",(attempt,)).fetchone():
                return False
            paused=self.db.execute('SELECT stopped_reason FROM batches WHERE digest=?',(key,)).fetchone()
            if not paused or not paused[0]: raise ValueError('Recovery requires paused batch')
            row=self.db.execute('SELECT * FROM jobs_v2 WHERE batch=? AND attempt_id=?',(key,attempt)).fetchone()
            now=self.clock()
            if not row or not row['owner'] or not row['lease_until'] or row['lease_until']>now or row['state'] not in ('claimed','verifying'):
                raise ValueError('Expected expired verification owner absent')
            old=self.db.execute('SELECT * FROM store_verification_v2 WHERE attempt_id=?',(attempt,)).fetchone()
            if not old or old['finished_at'] is not None or old['outcome'] is not None:
                raise ValueError('Cannot overwrite completed/checkpoint evidence')
            due=retry_time(dict(row),'temporarily_unreachable',now=datetime.fromtimestamp(now,timezone.utc))
            result={'state':'temporarily_unreachable','failure':'interrupted_unknown',
                    'request_accounting':'unknown','recovery':'expired_attempt_reconciled'}
            self.db.execute("UPDATE store_verification_v2 SET finished_at=?,outcome='interrupted_unknown',result_json=?,result_hash=? WHERE attempt_id=?",
                            (now,encoded(result),digest(result),attempt))
            self.db.execute("UPDATE jobs_v2 SET state='failed',owner=NULL,lease_until=NULL,next_due=? WHERE canonical=?",(due,row['canonical']))
            self.event(attempt,'expired_attempt_reconciled')
            return True

    def claim(self,key):
        now=self.clock();manifest=self.manifest(key)
        with self.transaction():
            b=self.db.execute('SELECT stopped_reason FROM batches WHERE digest=?',(key,)).fetchone()
            if now>=datetime.fromisoformat(manifest['expires_at']).timestamp(): return None
            selected=None
            if self.canary:
                if b[0]!='access_failure_rate': raise ValueError('Historical pause drift')
                if self.db.execute('SELECT 1 FROM jobs_v2 WHERE owner IS NOT NULL').fetchone():
                    raise ValueError('Canary ownership requires explicit review')
                from .canary import next_domain
                selected=next_domain(self,key)
                if selected is None: return None
            elif b[0]: return None
            # Expired children cannot commit: no database is accessible to them.
            # Interrupted verification is quarantined, not mislabeled completed.
            expired=self.db.execute('SELECT * FROM jobs_v2 WHERE owner IS NOT NULL AND lease_until<=?',(now,)).fetchall()
            for r in expired:
                saved=r['state'] in ('verified','classifying')
                self.db.execute('UPDATE jobs_v2 SET state=?,owner=NULL,lease_until=NULL,next_due=? WHERE canonical=?',
                                ('verified' if saved else 'failed',now if saved else now+3600,r['canonical']))
                if not saved:
                    self.db.execute("UPDATE store_verification_v2 SET outcome='interrupted_unknown',finished_at=? WHERE attempt_id=? AND finished_at IS NULL",(now,r['attempt_id']))
                self.event(r['attempt_id'],'lease_expired_classification_resumable' if saved else 'interrupted_unknown')
            # One active verification/classification across all batch manifests.
            if self.db.execute('SELECT 1 FROM jobs_v2 WHERE owner IS NOT NULL AND lease_until>?',(now,)).fetchone(): return None
            count=self.db.execute('SELECT count(*) FROM store_index_v2 WHERE eligible=1').fetchone()[0]
            if count>=manifest['target_eligible']: return None
            row=self.db.execute("SELECT j.*,s.fetch_host,s.row_json FROM jobs_v2 j JOIN store_index_v2 s USING(canonical) WHERE j.batch=? AND j.owner IS NULL AND j.state IN ('pending','failed','verified') AND j.next_due<=? AND (j.state='verified' OR j.attempts<?) ORDER BY CASE WHEN j.state='verified' THEN 0 ELSE 1 END,j.attempts,j.canonical LIMIT 1",
                                (key,now,manifest['per_domain_attempt_cap'])).fetchone()
            if selected:
                row=self.db.execute("SELECT j.*,s.fetch_host,s.row_json FROM jobs_v2 j JOIN store_index_v2 s USING(canonical) WHERE j.batch=? AND j.canonical=? AND j.owner IS NULL AND j.state='pending' AND j.attempts=0 AND j.next_due<=?",(key,selected,now)).fetchone()
                if not row: raise ValueError('Selected canary job no longer unattempted')
            if not row: return None
            row=dict(row);resume=row['state']=='verified'
            if not resume:
                spent=self.db.execute('SELECT count(*),coalesce(sum(reserved_requests),0),max(started_at) FROM store_verification_v2 WHERE batch=?',(key,)).fetchone()
                if spent[0]>=manifest['attempt_cap'] or spent[1]+8>manifest['request_cap']: return None
                last_start=self.db.execute('SELECT max(started_at) FROM store_verification_v2').fetchone()[0]
                if last_start is not None and now-last_start<manifest['min_start_gap_seconds']: return None
                row['attempt_id']=str(uuid.uuid4())
            row['owner']=str(uuid.uuid4());row['lease_until']=now+manifest['lease_seconds']
            row['state']='verified' if resume else 'claimed'
            row['attempts']+=int(not resume)
            self.db.execute('UPDATE jobs_v2 SET owner=?,lease_until=?,state=?,attempts=?,attempt_id=? WHERE canonical=?',
                (row['owner'],row['lease_until'],row['state'],row['attempts'],row['attempt_id'],row['canonical']))
            if not resume:
                self.db.execute('INSERT INTO store_verification_v2(attempt_id,canonical,batch,owner,started_at,reserved_requests) VALUES (?,?,?,?,?,8)',
                    (row['attempt_id'],row['canonical'],key,row['owner'],now))
            self.event(row['attempt_id'],'classification_reclaimed' if resume else 'claimed')
            return row

    def renew(self,job):
        with self.transaction():
            self._owned(job)
            reason=self.db.execute('SELECT stopped_reason FROM batches WHERE digest=?',(job['batch'],)).fetchone()[0]
            if reason and not (self.canary and reason=='access_failure_rate'):
                raise LostLease('Batch stopped')
            self.db.execute('UPDATE jobs_v2 SET lease_until=? WHERE canonical=?',(self.clock()+180,job['canonical']))

    def transition(self,job,state):
        with self.transaction():
            row=self._owned(job)
            if (row['state'],state) not in {('claimed','verifying'),('verified','classifying')}:
                raise ValueError('Invalid stage transition')
            self.db.execute('UPDATE jobs_v2 SET state=? WHERE canonical=?',(state,job['canonical']))
            if state=='classifying':
                self.db.execute('INSERT OR IGNORE INTO store_classification_v2(attempt_id,attempted_at) VALUES (?,?)',(job['attempt_id'],self.clock()))
            self.event(job['attempt_id'],state)

    def verified(self,job,row,result):
        with self.transaction():
            owned=self._owned(job)
            if owned['state']!='verifying': raise ValueError('No active verification')
            self.db.execute('UPDATE store_index_v2 SET row_json=?,eligible=0,exclusion=?,updated_at=? WHERE canonical=?',
                            (encoded(row),'classification_pending',self.clock(),job['canonical']))
            self.db.execute("UPDATE jobs_v2 SET state='verified' WHERE canonical=?",(job['canonical'],))
            self.db.execute("UPDATE store_verification_v2 SET outcome='verified',result_json=? WHERE attempt_id=?",(encoded(result),job['attempt_id']))
            self.event(job['attempt_id'],'verified')

    def complete(self,job,*,row=None,eligible=False,reason=None,retry_at=None,result=None,classification_metrics=None):
        if result is not None: result=self.with_protection(job,result,False)
        payload={'row':row,'eligible':eligible,'reason':reason,'retry_at':retry_at,'result':result,'classification_metrics':classification_metrics}
        completion=encoded({'attempt':job['attempt_id'],'owner':job['owner'],'hash':digest(payload)})
        with self.transaction():
            current=self.db.execute('SELECT * FROM jobs_v2 WHERE canonical=?',(job['canonical'],)).fetchone()
            if current['last_result']==completion: return False  # exact idempotent replay
            current=self._owned(job)
            classified=current['state']=='classifying'
            if eligible and (not classified or not row): raise ValueError('Eligibility requires saved classification')
            state='eligible' if eligible else 'failed' if retry_at is not None else 'ineligible'
            now=self.clock()
            self.db.execute('UPDATE jobs_v2 SET state=?,owner=NULL,lease_until=NULL,next_due=?,last_result=? WHERE canonical=?',
                            (state,retry_at or 0,completion,job['canonical']))
            self.db.execute('UPDATE store_index_v2 SET row_json=coalesce(?,row_json),eligible=?,exclusion=?,updated_at=? WHERE canonical=?',
                            (encoded(row) if row else None,int(eligible),reason,now,job['canonical']))
            self.db.execute('UPDATE store_verification_v2 SET finished_at=?,outcome=?,result_json=coalesce(?,result_json),result_hash=? WHERE attempt_id=?',
                            (now,'verified' if classified else reason,encoded(result) if result else None,digest(payload),job['attempt_id']))
            if classified:
                self.db.execute('UPDATE store_classification_v2 SET saved_at=?,confidence=?,eligible=?,exclusion=?,result_json=?,metrics_json=? WHERE attempt_id=?',
                                (now,row.get('category_confidence'),int(eligible),reason,encoded(row),encoded(classification_metrics or {}),job['attempt_id']))
            self.event(job['attempt_id'],state)
            outcomes=self.db.execute('SELECT outcome,result_json FROM store_verification_v2 WHERE batch=? AND finished_at IS NOT NULL',(job['batch'],)).fetchall()
            if len(outcomes)>=20:
                from .protection import has_protection
                blocked=sum(has_protection(r[0],json.loads(r[1] or '{}')) for r in outcomes)
                temporary=sum(r[0] in ('temporarily_unreachable','interrupted_unknown','child_timeout') for r in outcomes)
                if not self.canary and (blocked/len(outcomes)>.30 or temporary/len(outcomes)>.25):
                    self.pause(job['batch'],'access_failure_rate')
            # Reuse the existing 20-attempt / >25% failure budget: six
            # timeouts in the latest 20 completions pause even during startup.
            # One isolated safely terminated timeout remains independently retryable.
            recent=self.db.execute('SELECT outcome FROM store_verification_v2 WHERE batch=? AND finished_at IS NOT NULL ORDER BY finished_at DESC,rowid DESC LIMIT 20',(job['batch'],)).fetchall()
            if sum(r[0]=='child_timeout' for r in recent)>20*.25:
                self.pause(job['batch'],'child_timeout_rate')
            if reason in ('memory_ceiling','invalid_child_result','interrupted_shutdown'):
                self.pause(job['batch'],reason)
        return True

    def rows(self, *, eligible_only=False):
        condition=' AND eligible=1' if eligible_only else ''
        return [json.loads(r[0]) for r in self.db.execute('SELECT row_json FROM store_index_v2 WHERE row_json IS NOT NULL'+condition+' ORDER BY canonical')]

    def summary(self):
        return {'states':dict(self.db.execute('SELECT state,count(*) FROM jobs_v2 GROUP BY state')),
            'attempts':self.db.execute('SELECT count(*) FROM store_verification_v2').fetchone()[0],
            'reserved_requests':self.db.execute('SELECT coalesce(sum(reserved_requests),0) FROM store_verification_v2').fetchone()[0],
            'classification_attempted':self.db.execute('SELECT count(*) FROM store_classification_v2').fetchone()[0],
            'classification_saved':self.db.execute('SELECT count(*) FROM store_classification_v2 WHERE saved_at IS NOT NULL').fetchone()[0],
            'eligible':self.db.execute('SELECT count(*) FROM store_index_v2 WHERE eligible=1').fetchone()[0],
            'stopped_batches':dict(self.db.execute('SELECT digest,stopped_reason FROM batches WHERE stopped_reason IS NOT NULL'))}

    def backup(self,target):
        if Path(target).exists(): raise FileExistsError('Backup target already exists')
        with closing(sqlite3.connect(target)) as copy: self.db.backup(copy)

    def metrics(self):
        """Explicit aggregate report; no catalog payloads or merchant records printed."""
        from collections import Counter
        attempts=self.db.execute('SELECT outcome,result_json,finished_at FROM store_verification_v2').fetchall()
        outcomes=Counter(r['outcome'] or 'unfinished' for r in attempts)
        requests=0;seconds=[];peaks=[];unknown=0
        for r in attempts:
            result=json.loads(r['result_json'] or '{}')
            requests+=len(result.get('requests') or [])
            if r['finished_at'] is None or r['outcome'] in ('interrupted_unknown','child_timeout'): unknown+=1
            if result.get('supervisor_seconds') is not None: seconds.append(result['supervisor_seconds'])
            if result.get('peak_rss_kib') is not None: peaks.append(result['peak_rss_kib'])
        classified=self.db.execute('SELECT confidence,metrics_json FROM store_classification_v2 WHERE saved_at IS NOT NULL').fetchall()
        class_seconds=[]
        for r in classified:
            m=json.loads(r['metrics_json'] or '{}')
            if m.get('supervisor_seconds') is not None: class_seconds.append(m['supervisor_seconds'])
            if m.get('peak_rss_kib') is not None: peaks.append(m['peak_rss_kib'])
        summary=self.summary()
        return {**summary,'verification_outcomes':dict(outcomes),'observed_wire_requests':requests,
            'attempts_with_incomplete_accounting':unknown,
            'observed_requests_per_verified_attempt':requests/outcomes['verified'] if outcomes['verified'] else None,
            'requests_note':'Incomplete attempts retain full request reservations; observed counts are a lower bound when accounting is incomplete.',
            'classification_confidence':dict(Counter(str(r['confidence']) for r in classified)),
            'classification_pass_rate':sum((r['confidence'] or 0)>=55 for r in classified)/len(classified) if classified else None,
            'verified_to_eligible_yield':summary['eligible']/outcomes['verified'] if outcomes['verified'] else None,
            'mean_verification_child_seconds':sum(seconds)/len(seconds) if seconds else None,
            'mean_classification_child_seconds':sum(class_seconds)/len(class_seconds) if class_seconds else None,
            'largest_child_peak_rss_kib':max(peaks) if peaks else None,
            'memory_note':'Child RSS is not whole-service/cgroup peak memory; retain Render memory/OOM metrics separately.'}
