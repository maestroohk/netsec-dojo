"""The shop's HTTPS site, using the certificate made at boot."""
import os
import ssl
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class H(BaseHTTPRequestHandler):
    server_version = "shop/1.0"

    def log_message(self, *a):
        pass

    def do_GET(self):
        body = ("<h1>Dojo Shop</h1><p>Secure checkout ready. Order code: %s</p>\n"
                % os.environ["DOJO_FLAG"]).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ctx.load_cert_chain("/etc/shop/server.crt", "/etc/shop/server.key")
srv = ThreadingHTTPServer(("0.0.0.0", 443), H)
srv.socket = ctx.wrap_socket(srv.socket, server_side=True)
srv.serve_forever()
