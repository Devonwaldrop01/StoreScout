"""OFFLINE feasibility tests, not an installable production observer.

Reuse the network-isolated real-route TLS fixture, never modify legacy code.
The fixture controller's in-process profiling installation is deliberately a
best-case cooperative injection, NOT proof that external attachment is possible.
"""
import pathlib

fixture = pathlib.Path('/validation/lifetime_counterexample.py').read_text()
prefix = fixture.split('with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:')[0]
exec(compile(prefix, 'lifetime_counterexample_fixture_prefix', 'exec'), globals())

observations = []
code = store_index.verify_and_store.__code__
def profile(frame, kind, arg):
    if frame.f_code is code and kind in ('call', 'return'):
        # Never inspect arguments, locals, return payloads, exception text or domains.
        observations.append({'kind': kind, 'wall': time.time(),
                             'thread': threading.get_native_id()})

def stack_count():
    count = 0
    for frame in sys._current_frames().values():
        while frame:
            if frame.f_code is code:
                count += 1
            frame = frame.f_back
    return count

with concurrent.futures.ThreadPoolExecutor(max_workers=3) as callers:
    list(callers.map(request, range(3)))
waitfor(lambda: blocked == 3)
assert not any(e['event'] == 'request_finished' for e in events)
preexisting_stack_count = stack_count()
assert preexisting_stack_count == 3
attachment_time = time.time()
threading.setprofile_all_threads(profile)
assert observations == [], 'no retrospective function entry should be manufactured'
release.set()
waitfor(lambda: len(writes) == 3)
waitfor(lambda: len([e for e in observations if e['kind'] == 'return']) == 3)
waitfor(lambda: len([e for e in events if e['event'] == 'request_finished']) == 3)
threading.setprofile_all_threads(None)
assert [e['kind'] for e in observations] == ['return'] * 3
assert max(writes) > attachment_time
route_case = dict(preexisting_active=preexisting_stack_count,
                  entry_events=0, return_events=3, fake_db_writes=3,
                  http_timeouts=3, events=list(observations))

# The default-executor mechanism also has work queued before any thread frame
# exists. A frame-only inventory misses it. Keep direct Future references only
# in the TEST CONTROLLER as ground truth, not in the proposed external observer.
release.clear()
pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
futures = [pool.submit(store_index.verify_and_store, DB(),
                      f'queued{i}.invalid', 'fixture') for i in range(3)]
waitfor(lambda: blocked == 4)
queued_truth = sum(not f.running() and not f.done() for f in futures)
running_truth = sum(f.running() for f in futures)
frame_inventory = stack_count()
assert (queued_truth, running_truth, frame_inventory) == (2, 1, 1)
observations.clear()
threading.setprofile_all_threads(profile)
release.set()
for future in futures:
    future.result(timeout=15)
pool.shutdown(wait=True)
threading.setprofile_all_threads(None)
queued_case = dict(queued_before_attachment=queued_truth,
                   active_before_attachment=running_truth,
                   frame_inventory=frame_inventory,
                   observed_entries=sum(e['kind']=='call' for e in observations),
                   observed_returns=sum(e['kind']=='return' for e in observations))
assert queued_case['observed_entries'] == 2 and queued_case['observed_returns'] == 3

# A return profile event occurs on exceptional unwind too. The remote state
# can differ while the local failure has the same shape; no payload is logged.
original_query = Query.execute
remote_states = []
for committed in (False, True):
    observations.clear()
    remote_writes = []
    def ambiguous_execute(self):
        if self.operation != 'read':
            if committed:
                remote_writes.append(1)
            raise TimeoutError('fixture response unavailable')
        return SimpleNamespace(data=None)
    Query.execute = ambiguous_execute
    threading.setprofile_all_threads(profile)
    raised = False
    try:
        store_index.verify_and_store(DB(), 'ambiguous.invalid', 'fixture')
    except TimeoutError:
        raised = True
    finally:
        threading.setprofile_all_threads(None)
    remote_states.append(dict(remote_commits=len(remote_writes),
                              local_timeout=raised,
                              profile_events=[e['kind'] for e in observations]))
Query.execute = original_query
assert remote_states[0]['profile_events'] == remote_states[1]['profile_events'] == ['call','return']
assert all(x['local_timeout'] for x in remote_states)
assert [x['remote_commits'] for x in remote_states] == [0,1]

server.should_exit = True
server_thread.join(timeout=10)
assert not server_thread.is_alive()
redis_server.shutdown(); redis_server.server_close()
assert violations == []
summary = dict(passed=True, source='288223a2acb62bd6893e3370268f854bb2e16b12',
               cooperative_install_only=True,
               real_route_late_attachment=route_case,
               preexisting_queued_work=queued_case,
               persistence_ambiguity=remote_states,
               production_observer_ready=False, violations=violations)
OUT.joinpath('observer-semantics.json').write_text(json.dumps(summary,indent=2))
print('OBSERVER_SEMANTICS '+json.dumps(summary),flush=True)
