"""Intranet report server over plain HTTP (no TLS)."""
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class H(BaseHTTPRequestHandler):
    server_version = "IntranetHTTP/1.0"

    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path == "/reports/status":
            body = ("report status: final\nreference: %s\n" % os.environ["DOJO_FLAG"]).encode()
        else:
            body = b"nothing here\n"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


ThreadingHTTPServer(("0.0.0.0", int(os.environ["DOJO_PORT"])), H).serve_forever()
