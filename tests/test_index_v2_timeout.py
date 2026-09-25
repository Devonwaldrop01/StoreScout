"""Independent timeout isolation and retained-evidence recovery regressions."""
import json
import subprocess
import sys
import time
import pytest
from test_index_v2 import store, manifest, executor, catalog
from index_v2.store import Store, LostLease
from index_v2.worker import ChildFailed, process_job


def confirmed_timeout(*args):
    error=ChildFailed('child_timeout');error.termination_confirmed=True
    raise error


def test_healthy_timeout_healthy_and_restart(store):
    key=store.seed(manifest(('a.com','b.com','c.com')))
    process_job(store,store.claim(key),executor);store.test_clock[0]+=11
    timed=store.claim(key);process_job(store,timed,confirmed_timeout)
    attempt=dict(store.db.execute('SELECT * FROM store_verification_v2 WHERE attempt_id=?',(timed['attempt_id'],)).fetchone())
    assert attempt['outcome']=='child_timeout' and attempt['finished_at'] and attempt['result_hash']
    assert attempt['reserved_requests']==8
    assert json.loads(attempt['result_json'])['request_accounting']=='unknown'
    assert not store.summary()['stopped_batches']
    reopened=Store(store.path,clock=store.clock)
    try:
        state=dict(reopened.db.execute("SELECT * FROM jobs_v2 WHERE canonical='b.com'").fetchone())
        assert state['state']=='failed' and state['owner'] is None and state['next_due']>store.clock()
        assert state['attempts']==1
        with pytest.raises(LostLease): reopened.complete(timed,reason='late_result')
        store.test_clock[0]+=11
        following=reopened.claim(key);assert following['canonical']=='c.com'
        process_job(reopened,following,executor)
        assert reopened.summary()['eligible']==2
        assert reopened.summary()['reserved_requests']==24
        assert reopened.metrics()['attempts_with_incomplete_accounting']==1
        assert reopened.claim(key) is None
    finally: reopened.close()


def test_repeated_timeouts_pause_without_crash(store):
    key=store.seed(manifest(tuple(f's{i:02}.com' for i in range(21))))
    for i in range(6):
        process_job(store,store.claim(key),confirmed_timeout);store.test_clock[0]+=11
        assert bool(store.summary()['stopped_batches'])==(i==5)
    assert store.summary()['stopped_batches'][key]=='child_timeout_rate'
    assert store.claim(key) is None
    assert store.summary()['reserved_requests']==48


def test_timeout_breaker_does_not_accumulate_old_isolated_failures(store):
    key=store.seed(manifest(tuple(f's{i:02}.com' for i in range(30))))
    for i in range(26):
        process_job(store,store.claim(key),confirmed_timeout if i in (0,1,2,3,4,25) else executor)
        store.test_clock[0]+=11
    assert not store.summary()['stopped_batches']


@pytest.mark.parametrize('reason',['child_termination_unconfirmed','memory_ceiling','invalid_child_result','child_exit_-9'])
def test_unsafe_child_failures_remain_immediate_pause(store,reason):
    key=store.seed(manifest());job=store.claim(key)
    def failure(*args): raise ChildFailed(reason)
    with pytest.raises(ChildFailed): process_job(store,job,failure)
    assert store.summary()['stopped_batches'][key]==reason
    assert store.claim(key) is None
    assert store.db.execute('SELECT finished_at FROM store_verification_v2').fetchone()[0] is None


def test_timeout_persistence_failure_stops_dispatch(store,monkeypatch):
    key=store.seed(manifest())
    def broken(*args,**kwargs): raise OSError('injected persistence failure')
    monkeypatch.setattr(store,'complete',broken)
    with pytest.raises(OSError): process_job(store,store.claim(key),confirmed_timeout)
    assert store.summary()['stopped_batches'][key]=='timeout_persistence_failed'
    assert store.claim(key) is None


def test_expired_recovery_is_paused_idempotent_and_cannot_duplicate(store):
    key=store.seed(manifest(('a.com','b.com')));old=store.claim(key)
    store.transition(old,'verifying');store.pause(key,'child_timeout')
    with pytest.raises(ValueError): store.recover_expired_attempt(key,old['attempt_id'])
    store.test_clock[0]+=181
    assert store.recover_expired_attempt(key,old['attempt_id'])
    evidence=[tuple(r) for r in store.db.execute('SELECT * FROM events_v2')]
    assert not store.recover_expired_attempt(key,old['attempt_id'])
    assert [tuple(r) for r in store.db.execute('SELECT * FROM events_v2')]==evidence
    assert store.claim(key) is None # Recovery is not authorization to resume.
    assert store.summary()['reserved_requests']==8 and store.summary()['attempts']==1
    with pytest.raises(LostLease): store.complete(old,reason='stale')
    store.db.execute('UPDATE batches SET stopped_reason=NULL WHERE digest=?',(key,)) # Synthetic test only.
    next_job=store.claim(key);assert next_job['canonical']=='b.com'
    assert store.claim(key) is None
    process_job(store,next_job,executor)
    store.test_clock[0]+=5000
    retry=store.claim(key);assert retry['canonical']=='a.com' and retry['attempts']==2
    assert retry['attempt_id']!=old['attempt_id'] and retry['owner']!=old['owner']
    assert store.claim(key) is None


def test_recovery_rejects_wrong_identity_active_batch_and_checkpoint(store):
    key=store.seed(manifest());job=store.claim(key)
    store.test_clock[0]+=181
    with pytest.raises(ValueError): store.recover_expired_attempt(key,job['attempt_id'])
    store.pause(key,'child_timeout')
    with pytest.raises(ValueError): store.recover_expired_attempt(key,'wrong')
    store.db.execute("UPDATE jobs_v2 SET state='verified'")
    with pytest.raises(ValueError): store.recover_expired_attempt(key,job['attempt_id'])


@pytest.mark.parametrize('html,expected',[
    ('<meta content="A small linen store" name="description">','A small linen store'),
    ("<META content='Maker &amp; home' NAME='DESCRIPTION'>",'Maker & home'),
    ('<meta content="No description here" name="other">',None),
    ('<meta content="other"><script>name="description"</script>',None),
    ('<meta content="unclosed',None),
])
def test_reversed_description_is_tag_scoped(html,expected):
    from app.services.store_index import _reversed_meta_description
    assert _reversed_meta_description(html)==expected


def test_adversarial_missing_description_is_bounded():
    # Independent synthetic markup, not a merchant/benchmark-specific rule.
    from app.services.store_index import _reversed_meta_description
    html='<meta content="'+('x\" data-v=\"'*15000)+'" name="other">'
    start=time.monotonic()
    assert _reversed_meta_description(html) is None
    assert time.monotonic()-start<3


def test_unclean_termination_never_certifies_timeout(monkeypatch):
    import index_v2.worker as worker
    real_terminate=worker.terminate
    def uncertain(p):
        real_terminate(p)
        raise ChildFailed('child_termination_unconfirmed')
    monkeypatch.setattr(worker,'terminate',uncertain)
    with pytest.raises(ChildFailed,match='termination_unconfirmed') as error:
        worker.execute_child({'stage':'classify','row':catalog()},lambda:None,lambda:True)
    assert not error.value.termination_confirmed


@pytest.mark.skipif(sys.platform!='linux',reason='Actual 90-second Linux subprocess deadline')
def test_linux_healthy_forced_timeout_healthy(store,monkeypatch):
    import index_v2.worker as worker
    original=worker.subprocess.Popen
    children=[]
    def launch(argv,**kwargs):
        if json.loads(kwargs['stdin'].read())['stage']=='verify':
            kwargs['stdin'].seek(0)
            argv=[sys.executable,'-c','from index_v2.child import limits; limits(); import time; time.sleep(180)']
        else: kwargs['stdin'].seek(0)
        p=original(argv,**kwargs);children.append(p);return p
    monkeypatch.setattr(worker.subprocess,'Popen',launch)
    key=store.seed(manifest(('a.com','b.com','c.com')))
    process_job(store,store.claim(key),executor);store.test_clock[0]+=11
    job=store.claim(key);start=time.monotonic()
    process_job(store,job,worker.execute_child)
    assert 90<=time.monotonic()-start<100
    assert children and all(p.poll() is not None for p in children)
    store.test_clock[0]+=11
    process_job(store,store.claim(key),executor)
    assert store.summary()['eligible']==2 and not store.summary()['stopped_batches']
