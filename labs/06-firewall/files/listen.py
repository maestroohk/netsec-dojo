"""Tiny TCP listener: accepts a connection, sends a banner, closes."""
import socket
import sys

s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("0.0.0.0", int(sys.argv[1])))
s.listen(50)
while True:
    c, _ = s.accept()
    try:
        c.sendall(sys.argv[2].encode() + b"\r\n")
    except OSError:
        pass
    c.close()
