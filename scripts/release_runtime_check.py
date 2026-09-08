"""Exercise an isolated Linux test stack. No production URLs or credentials."""
import json
import multiprocessing
import os
import ssl
import time

import httpx


def contender(start, release, results):
    from app.services.index_lease import acquire_stage
    os.environ['STORE_INDEX_DEPLOYMENT_HOLD'] = 'false'
    start.wait(10)
    lease = acquire_stage('release_test', 30)
    results.put(bool(lease))
    if lease:
        try:
            lease.require()
            release.wait(10)
        finally:
            lease.release()


if __name__ == '__main__':
    from app.core.config import get_settings
    from app.core.index_hold import index_writes_held, IndexDeploymentHeld
    from app.core.redis_connection import coordination_redis
    from app.tasks.celery_app import celery
    from app.tasks.store_index import stage_verification, verification_canary_wave
    from app.services.index_lease import acquire_stage
    assert get_settings().supabase_url == 'https://offline.invalid'
    assert index_writes_held() and not get_settings().store_index_canary_enabled
    assert not get_settings().anthropic_api_key
    assert stage_verification(force=True)['status'] == 'deployment_hold'
    assert verification_canary_wave()['status'] == 'deployment_hold'
    try:
        stage_verification.delay(force=True)
    except IndexDeploymentHeld:
        pass
    else:
        raise AssertionError('held task was published')
    connection = coordination_redis()
    assert connection.ping()
    actual = connection.connection_pool.get_connection()
    try:
        assert actual._sock.context.verify_mode == ssl.CERT_REQUIRED
        assert actual._sock.context.check_hostname
    finally:
        connection.connection_pool.release(actual)
    reply = None
    for _ in range(15):
        reply = celery.control.inspect(timeout=2).ping()
        if reply: break
        time.sleep(1)
    assert reply and all(v == {'ok':'pong'} for v in reply.values()), reply
    with httpx.Client(timeout=5) as client:
        assert client.get('http://web:10000/').status_code == 200
        response = client.post('http://web:10000/api/v1/internal/store-index/verify',
                               json={'domain':'never-fetch.invalid'}, headers={'x-internal-token':'offline-test'})
        assert response.status_code == 503 and response.json()['code'] == 'deployment_hold'
    start, release, results = multiprocessing.Event(), multiprocessing.Event(), multiprocessing.Queue()
    processes = [multiprocessing.Process(target=contender, args=(start, release, results)) for _ in range(2)]
    for p in processes: p.start()
    start.set()
    try:
        acquired = [results.get(timeout=15), results.get(timeout=15)]
        assert sorted(acquired) == [False, True], acquired
    finally:
        release.set()
        for p in processes: p.join(15)
    assert all(p.exitcode == 0 for p in processes)
    assert not connection.exists('lock:index:release_test')
    os.environ['STORE_INDEX_DEPLOYMENT_HOLD'] = 'false'
    lease = acquire_stage('release_test', 30)
    assert lease
    lease.require()
    os.environ['STORE_INDEX_DEPLOYMENT_HOLD'] = 'true'
    assert not lease.renew()
    lease.release()
    assert not connection.exists('lock:index:release_test')
    connection.close()
    print(json.dumps({'web':'healthy/held', 'worker':'pong/held', 'tls':'CERT_REQUIRED+hostname',
                      'two_process_exclusion':'passed', 'renew_release_recovery':'passed', 'canary':'disabled'}))
