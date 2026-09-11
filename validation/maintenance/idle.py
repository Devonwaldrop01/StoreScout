"""PROPOSAL ONLY: inert worker/Beat process; no broker or database connection."""
import signal
import threading

stopped = threading.Event()
signal.signal(signal.SIGTERM, lambda *_: stopped.set())
signal.signal(signal.SIGINT, lambda *_: stopped.set())
print("STORE_INDEX_MAINTENANCE_BRIDGE idle; application not imported", flush=True)
stopped.wait()
print("STORE_INDEX_MAINTENANCE_BRIDGE clean exit", flush=True)
