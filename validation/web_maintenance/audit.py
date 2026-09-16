"""Non-production audit runner; fails on application imports or outbound sockets."""
import json
import runpy
import sys

events = []
blocked = ("app", "celery", "redis", "supabase", "postgrest")
def audit(event, args):
    if event == "import" and args[0].split(".")[0] in blocked:
        events.append([event, args[0]])
        raise RuntimeError("Forbidden import")
    if event in ("socket.connect", "socket.sendto"):
        events.append([event])
        raise RuntimeError("Forbidden outbound connection")
sys.addaudithook(audit)
try:
    runpy.run_path("/app/scripts/store_web_maintenance.py", run_name="__main__")
finally:
    imported = sorted(n for n in sys.modules if n.split(".")[0] in blocked)
    print("ISOLATION_AUDIT " + json.dumps({"forbidden_events": events, "forbidden_modules": imported}), flush=True)
    assert not events and not imported
