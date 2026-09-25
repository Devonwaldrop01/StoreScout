"""Explicit one-shot diagnostic scope; never clears the historical batch pause."""
import json
from pathlib import Path
from .identity import digest,canonical

SPEC=Path(__file__).with_name('protection_canary_10.json')
SPEC_SHA='08412f9f30ec83f11ddac1a40d2669b38887aea22181a07383114c9811472b4b'


def load():
    spec=json.loads(SPEC.read_text(encoding='utf8'))
    if digest(spec)!=SPEC_SHA: raise ValueError('Canary manifest identity differs')
    return spec


def marker(spec): return 'protection_canary:'+digest(spec)


def stopped(store):
    return bool(store.canary and store.db.execute("SELECT 1 FROM events_v2 WHERE attempt_id=? AND state LIKE 'stopped_%'",(marker(store.canary),)).fetchone())


def validate(store,spec,*,arming=False):
    domains=spec['domains']
    if len(domains)!=10 or len(set(domains))!=10 or any(canonical(d)!=d for d in domains):
        raise ValueError('Canary requires ten distinct canonical domains')
    if spec['max_attempts']!=10 or spec['max_reserved_requests']!=80: raise ValueError('Canary budget differs')
    manifest=store.manifest(spec['batch'])
    if manifest['min_start_gap_seconds']!=10 or manifest['per_domain_attempt_cap']!=3: raise ValueError('Canary policy drift')
    rows=[dict(r) for r in store.db.execute('SELECT * FROM store_verification_v2 ORDER BY attempt_id')]
    baseline=spec['baseline_attempts']
    old=[r for r in rows if r['attempt_id'] in baseline]
    if len(old)!=len(baseline) or any(digest(r)!=baseline[r['attempt_id']] for r in old):
        raise ValueError('Original attempt evidence changed')
    new=[r for r in rows if r['attempt_id'] not in baseline]
    if len(new)>10 or sum(r['reserved_requests'] for r in new)>80 or len({r['canonical'] for r in new})!=len(new):
        raise ValueError('Canary budget/duplicate failure')
    if any(r['batch']!=spec['batch'] or r['canonical'] not in domains or r['reserved_requests']!=8 for r in new):
        raise ValueError('Out-of-scope attempt detected')
    if arming:
        if new: raise ValueError('Cannot arm after new work')
        pending={r[0] for r in store.db.execute("SELECT canonical FROM jobs_v2 WHERE batch=? AND state='pending' AND attempts=0 AND owner IS NULL",(spec['batch'],))}
        expected=[e['canonical'] for e in manifest['entries'] if e['canonical'] in pending][:10]
        if expected!=domains: raise ValueError('Manifest-order pending slice differs')
        if store.db.execute('SELECT 1 FROM jobs_v2 WHERE owner IS NOT NULL').fetchone(): raise ValueError('Existing owner')
    return new


def arm(store,spec):
    """Separate operator action, never called by startup or deploy."""
    with store.transaction():
        if store.db.execute("SELECT 1 FROM events_v2 WHERE attempt_id=? AND state='armed'",(marker(spec),)).fetchone(): return False
        validate(store,spec,arming=True)
        reason=store.db.execute('SELECT stopped_reason FROM batches WHERE digest=?',(spec['batch'],)).fetchone()[0]
        if reason!='access_failure_rate': raise ValueError('Unexpected historical pause')
        store.event(marker(spec),'armed')
        return True


def next_domain(store,key):
    spec=store.canary
    if key!=spec['batch']: raise ValueError('Wrong canary batch')
    if stopped(store) or not store.db.execute("SELECT 1 FROM events_v2 WHERE attempt_id=? AND state='armed'",(marker(spec),)).fetchone(): return None
    new=validate(store,spec)
    if any(r['finished_at'] is None for r in new):
        raise ValueError('Unfinished canary attempt requires explicit review')
    if any(r['outcome'] in ('child_timeout','interrupted_unknown') for r in new):
        store.pause(key,'canary_incomplete_accounting');return None
    done={r['canonical'] for r in new}
    if len(done)==10:
        store.pause(key,'canary_complete');return None
    return next(d for d in spec['domains'] if d not in done)
