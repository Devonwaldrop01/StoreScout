#!/usr/bin/python -ISB
"""Standalone maintenance listener. Never import StoreScout or contact services."""
import os
import signal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MESSAGE = b"StoreScout is temporarily undergoing maintenance.\n"
READY = b"StoreScout maintenance listener ready; application unavailable.\n"
READY_PATH = "/__maintenance/ready"


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "StoreScoutMaintenance"
    sys_version = ""

    def setup(self):
        self.request.settimeout(2)
        super().setup()

    def respond(self):
        ready = self.command in ("GET", "HEAD") and self.path == READY_PATH
        body = READY if ready else MESSAGE
        self.send_response(200 if ready else 503)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-StoreScout-Mode", "maintenance")
        self.send_header("Connection", "close")
        if not ready:
            self.send_header("Retry-After", "60")
        self.end_headers()
        self.close_connection = True
        if self.command != "HEAD":
            self.wfile.write(body)

    do_GET = do_HEAD = do_POST = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = respond

    def handle_expect_100(self):
        self.respond()
        return False

    def log_message(self, format, *args):
        pass  # Do not log request URLs, credentials or bodies.


def main():
    port = int(os.environ["PORT"])
    if not 1 <= port <= 65535:
        raise ValueError("PORT must be between 1 and 65535")
    stopping = False

    def stop(signum, frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    with ThreadingHTTPServer(("0.0.0.0", port), Handler) as server:
        server.timeout = 0.2
        print(f"STORE_WEB_MAINTENANCE ready 0.0.0.0:{port}; application unavailable", flush=True)
        while not stopping:
            server.handle_request()
    print("STORE_WEB_MAINTENANCE clean exit", flush=True)


if __name__ == "__main__":
    main()
