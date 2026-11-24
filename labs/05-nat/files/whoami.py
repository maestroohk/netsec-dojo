"""A public website that tells visitors which address it saw them come from."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class H(BaseHTTPRequestHandler):
    server_version = "whoami/1.0"

    def log_message(self, *a):
        pass

    def do_GET(self):
        body = ("Hello from the internet.\nYour address: %s\n" % self.client_address[0]).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


ThreadingHTTPServer(("0.0.0.0", 80), H).serve_forever()
