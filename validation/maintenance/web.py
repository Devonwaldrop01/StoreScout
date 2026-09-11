"""PROPOSAL ONLY: inert maintenance listener; never imports StoreScout."""
import os
import signal
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BODY = b"StoreScout maintenance. Please retry later.\n"

class MaintenanceHandler(BaseHTTPRequestHandler):
    def reply(self):
        self.send_response(503)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(BODY)))
        self.send_header("Retry-After", "60")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True
        if self.command != "HEAD":
            self.wfile.write(BODY)

    do_GET = do_HEAD = do_POST = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = reply

    def log_message(self, *args):
        pass

server = ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", "10000"))), MaintenanceHandler)
server.daemon_threads = True
# PID 1 must explicitly handle SIGTERM; never rely on Docker's later SIGKILL.
signal.signal(signal.SIGTERM, lambda *_: threading.Thread(target=server.shutdown, daemon=True).start())
signal.signal(signal.SIGINT, lambda *_: threading.Thread(target=server.shutdown, daemon=True).start())
print("STORE_INDEX_MAINTENANCE_BRIDGE web inert; application not imported", flush=True)
try:
    server.serve_forever(poll_interval=0.5)
finally:
    server.server_close()
print("STORE_INDEX_MAINTENANCE_BRIDGE clean exit", flush=True)
