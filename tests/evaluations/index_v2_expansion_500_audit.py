"""Read-only reconciliation of the halted 500-domain expansion; no network/run.

Requires retained outputs/index-v2-expansion-500 and original pilot SQLite.
Does not clear leases, reclassify an unknown attempt, or invoke a benchmark.
"""
import collections
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import statistics
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from index_v2.identity import digest, validate
from index_v2.experiment import eligible_rows

OUT = ROOT/'outputs/index-v2-expansion-500'
DOC = ROOT/'docs/quality-audit/index-v2/expansion-500'
KEY = '53a05af3f1551a12a79ade3768e011cd559e5857b847a0e4782efa54d3696c37'
load = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
utc = lambda t: datetime.fromtimestamp(t, timezone.utc).isoformat()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    original = ROOT/'outputs/index-v2-pilot-100/pilot-results-20260922.sqlite'
    snapshot = OUT/'expansion-stopped-20260925.sqlite'
    assert sha(original) == '6c5b00b34188892f87cba9a6a7b6ede520c4d237d547f14264236e10538c5a26'
    assert sha(snapshot) == load(OUT/'stopped-backup-receipt.json')['backup_sha256']
    old = sqlite3.connect(original.as_uri()+'?mode=ro&immutable=1', uri=True)
    db = sqlite3.connect(snapshot.as_uri()+'?mode=ro&immutable=1', uri=True)
    db.row_factory = sqlite3.Row
    assert db.execute('pragma integrity_check').fetchone()[0] == 'ok'
    assert not db.execute('pragma foreign_key_check').fetchall()
    manifest = validate(load(DOC/'manifest-500.json'))
    assert digest(manifest) == KEY
    assert json.loads(db.execute('select manifest from batches where digest=?', (KEY,)).fetchone()[0]) == manifest
    # Verify all pilot rows survive exactly, across every data/queue/audit table.
    preserved = {}
    for table in ['batches','store_index_v2','provenance_v2','jobs_v2','store_verification_v2','store_classification_v2','events_v2']:
        previous = set(old.execute('select * from '+table).fetchall())
        current = {tuple(r) for r in db.execute('select * from '+table)}
        assert previous <= current, table
        preserved[table] = len(previous)
    jobs = [dict(r) for r in db.execute('select * from jobs_v2 where batch=? order by canonical', (KEY,))]
    assert len(jobs) == 500 and {j['canonical'] for j in jobs} == {e['canonical'] for e in manifest['entries']}
    attempts = [dict(r) for r in db.execute('select * from store_verification_v2 where batch=? order by started_at', (KEY,))]
    finished = [a for a in attempts if a['finished_at'] is not None]
    unfinished = [a for a in attempts if a['finished_at'] is None]
    assert len(attempts) == 9 and len(finished) == 8 and len(unfinished) == 1
    assert unfinished[0]['canonical'] == '5to9vibe.com'
    assert unfinished[0]['result_json'] is None and unfinished[0]['result_hash'] is None
    assert all(j['attempts'] == sum(a['canonical']==j['canonical'] for a in attempts) for j in jobs)
    requests = [r for a in finished for r in json.loads(a['result_json'])['requests']]
    assert len(requests) == 30 and all(len(json.loads(a['result_json'])['requests']) <= 8 for a in finished)
    assert all(a['reserved_requests'] == 8 for a in attempts)
    classes = [dict(r) for r in db.execute('select c.* from store_classification_v2 c join store_verification_v2 v using(attempt_id) where v.batch=?', (KEY,))]
    assert len(classes) == 7 and all(c['saved_at'] is not None for c in classes)
    assert sum(c['eligible'] for c in classes) == 4
    events = dict(db.execute('select e.state,count(*) from events_v2 e join store_verification_v2 v using(attempt_id) where v.batch=? group by e.state', (KEY,)))
    assert events == {'claimed':9,'verifying':9,'verified':7,'classifying':7,'eligible':4,'ineligible':3,'failed':1,'supervisor_stopped_child_timeout':1}
    assert db.execute('select stopped_reason from batches where digest=?', (KEY,)).fetchone()[0] == 'child_timeout'
    logs = load(OUT/'render-runtime-logs.json')
    assert not logs['hasMore']
    restarts = [r for r in logs['logs'] if 'restarted' in r['message']]
    assert len(restarts) == 1
    timeout = db.execute("select max(at) from events_v2 where state='supervisor_stopped_child_timeout'").fetchone()[0]
    disabled = next(r['timestamp'] for r in logs['logs'] if 'STORE_INDEX_V2 disabled' in r['message'])
    # Python accepts nanosecond text and retains microsecond precision.
    disabled_ts = datetime.fromisoformat(disabled.replace('Z','+00:00')).timestamp()
    monitor = [json.loads(line) for line in (OUT/'monitor.jsonl').read_text(encoding='utf-8-sig').splitlines() if line.strip()]
    active = [m for m in monitor if m['enabled'] == 'true']
    metrics = load(OUT/'render-metrics.json')
    cpu = [v['value'] for m in metrics['metrics'] if m['type']=='cpu_usage' for series in m['data']
           if any(l['field']=='instance' and l['value'].endswith('-z9fdg') for l in series['labels']) for v in series['values']]
    confidence = [c['confidence'] for c in classes]
    eligible = [json.loads(r[0]) for r in db.execute('select row_json from store_index_v2 where eligible=1')]
    final = load(OUT/'final-disabled.json')
    assert final['enabled']=='false' and final['attempts']==9 and final['pilot_attempts']==102
    assert final['requests']==30 and final['paused']=={KEY:'child_timeout'}
    assert final['expired_owners']==1
    assert final['bad_events']==[{'state':'supervisor_stopped_child_timeout','n':1}]
    baseline = load(ROOT/'outputs/discovery-quality-fixed-supply/legacy.json')
    asof = datetime.fromtimestamp(load(OUT/'stopped-backup-receipt.json')['at'],timezone.utc)
    combined = eligible_rows(baseline+eligible, asof)
    assert len(eligible) == 58 and len(combined) == 92
    output = {
      'status':'STOPPED_INCOMPLETE', 'batch':KEY, 'source_sha':'f2ae2e8ebdba902eead2aa376e845da530259c4e',
      'matching_sha':'34b550436ca8a4bf670e17123dcdd26d03ede750',
      'registry_digest':'sha256:9c88545592aebe38db653c4d9ffd0cad02dda767fce5e06872096d42d676f385',
      'imported':500,'attempted':9,'completed_first_pass':8,'unattempted':491,'retries':0,
      'verified_readable':7,'temporarily_unreachable':1,'timeout_unknown':1,
      'blocked_recorded':0,'unavailable_recorded':0,'unreadable_recorded':0,'ambiguous_recorded':0,'other_recorded':0,
      'classification_attempted':7,'classification_saved':7,'eligible_added':4,'below_threshold':3,
      'eligible_fraction_of_attempted_partial':4/9,'eligible_fraction_of_imported_not_final_yield':4/500,
      'final_500_domain_yield':None,
      'confidence':{'values':sorted(confidence),'mean':statistics.mean(confidence),'median':statistics.median(confidence),
        'bins':{k:sum(lo<=c<hi for c in confidence) for k,lo,hi in [('0',0,1),('1-54',1,55),('55-69',55,70),('70-84',70,85),('85-100',85,101)]}},
      'recorded_requests':30,'unknown_attempt_request_reservation':8,'possible_total_requests_interval':[30,38],
      'total_reserved_requests':72,'requests_per_verified_interval':[30/7,38/7],
      'unknown_accounting_retained':True,'budgets_refunded':False,
      'first_attempt_at':utc(attempts[0]['started_at']),'timeout_at':utc(timeout),'disabled_log_at':disabled,
      'execution_seconds_to_stop':timeout-attempts[0]['started_at'],
      'enabled_seconds_through_disabled_log':disabled_ts-attempts[0]['started_at'],
      'completed_domains_per_hour_until_stop':8*3600/(timeout-attempts[0]['started_at']),
      'throughput_caution':'Interrupted 8-completion sample; not a completed-batch capacity estimate.',
      'observed_memory_peak_bytes':max(m['memory_peak'] for m in active),
      'memory_peak_limit':'Recorded pre-restart cgroup peak; final old-cgroup peak unavailable after restart.',
      'sampled_cpu_peak_cores':max(cpu),'sampled_cpu_mean_cores':statistics.mean(cpu),'cpu_samples':len(cpu),
      'observed_cpu_seconds_before_restart':max(m['cpu_stat']['usage_usec'] for m in active)/1e6,
      'oom_events_observed':max(m['memory_events'].get('oom',0) for m in monitor),
      'unexpected_process_restarts':len(restarts),'duplicate_jobs':0,'stale_completion_events':0,
      'unresolved_lease_rows':1,'lease_expiry_at':utc(next(j['lease_until'] for j in jobs if j['owner'])),
      'lease_note':'Retained verifying/owner row for the terminated attempt; batch pause prevents reclaim. No lease or budget reset performed.',
      'final_disabled_at':utc(final['at']),'final_instance':final['instance'],'final_expired_owner_rows':final['expired_owners'],
      'pilot_rows_preserved_exactly':preserved,
      'disk':{'pilot_snapshot_bytes':original.stat().st_size,'stopped_snapshot_bytes':snapshot.stat().st_size,
        'logical_snapshot_growth_bytes':snapshot.stat().st_size-original.stat().st_size,
        'max_observed_live_file_bytes':max(m['disk_file_bytes'] for m in active),
        'live_file_caution':'Includes pre-expansion backup, manifests, main DB, WAL/SHM; do not equate with pure catalog growth.'},
      'total_v2_eligible':58,'legacy_eligible':34,'combined_eligible_partial':92,
      'benchmark_run':False,'expanded_ceiling':None,'decision_ABC':None,
      'recommendation':'Resolve the bounded verification child timeout and its unaccounted attempt offline before requesting recovery/resume. No evidence supports an A/B/C expansion decision from nine attempted domains.',
      'events':events,
      'per_attempt':[{'canonical':a['canonical'],'started_at':utc(a['started_at']),'finished_at':utc(a['finished_at']) if a['finished_at'] else None,'outcome':a['outcome'],'reserved_requests':a['reserved_requests'],'recorded_requests':len(json.loads(a['result_json'] or '{}').get('requests',[])) if a['result_json'] else None} for a in attempts],
      'hashes':{p.relative_to(ROOT).as_posix():sha(p) for p in [original,snapshot,DOC/'manifest-500.json',OUT/'render-runtime-logs.json',OUT/'render-metrics.json',OUT/'monitor.jsonl',OUT/'final-disabled.json']},
    }
    (DOC/'stopped-audit.json').write_text(json.dumps(output,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:output[k] for k in ['status','imported','attempted','completed_first_pass','unattempted','verified_readable','eligible_added','confidence','execution_seconds_to_stop','enabled_seconds_through_disabled_log','completed_domains_per_hour_until_stop','observed_memory_peak_bytes','sampled_cpu_peak_cores','disk','total_v2_eligible','combined_eligible_partial','pilot_rows_preserved_exactly']},indent=2))
    old.close();db.close()


if __name__=='__main__':
    main()
