"""Disposable fake DB recorder on an internal Docker network, no real data."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

class Sink(BaseHTTPRequestHandler):
    def respond(self):
        self.rfile.read(int(self.headers.get("Content-Length", "0")))
        with Path("/tmp/requests.jsonl").open("a") as f:
            f.write(json.dumps({"method": self.command, "path": self.path}) + "\n")
        body = json.dumps([{"key": "shopify_index_enabled", "value": True}]
                          if "app_config" in self.path else []).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    do_GET = do_POST = do_PATCH = do_DELETE = do_PUT = respond
    def log_message(self, *args):
        pass

ThreadingHTTPServer(("0.0.0.0", 8080), Sink).serve_forever()
