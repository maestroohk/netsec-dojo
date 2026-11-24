"""Simulated services for the scanning lab. Each port greets with a banner."""
import asyncio
import os
import sys

FLAG = os.environ.get("DOJO_FLAG", "")


def banner(text):
    async def handle(reader, writer):
        writer.write(text)
        try:
            await writer.drain()
            await asyncio.wait_for(reader.read(100), timeout=5)
        except Exception:
            pass
        writer.close()
    return handle


async def http(reader, writer):
    try:
        await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=5)
        body = b"<html><title>Acme staging</title><h1>It works</h1></html>\n"
        writer.write(b"HTTP/1.1 200 OK\r\nServer: nginx/1.18.0\r\nContent-Type: text/html\r\n"
                     b"Content-Length: %d\r\nConnection: close\r\n\r\n" % len(body) + body)
        await writer.drain()
    except Exception:
        pass
    writer.close()


async def dojod(reader, writer):
    writer.write(b"dojod 1.3.7 ready. Send HELP.\n")
    try:
        await writer.drain()
        while True:
            line = (await asyncio.wait_for(reader.readline(), timeout=30)).strip().upper()
            if not line or line == b"QUIT":
                break
            if line == b"HELP":
                writer.write(b"commands: HELP, FLAG, QUIT\n")
            elif line == b"FLAG":
                writer.write(FLAG.encode() + b"\n")
            else:
                writer.write(b"unknown command\n")
            await writer.drain()
    except Exception:
        pass
    writer.close()


async def main(role):
    if role == "target":
        services = {21: banner(b"220 ProFTPD 1.3.5 Server (Acme FTP) ready.\r\n"),
                    80: http,
                    3306: banner(b"5.7.33-log MySQL Community Server\n"),
                    int(os.environ["DOJO_PORT"]): dojod}
    else:
        services = {631: banner(b"CUPS/2.3 IPP\r\n"), 9100: banner(b"@PJL INFO STATUS\r\n")}
    servers = [await asyncio.start_server(h, "0.0.0.0", p) for p, h in services.items()]
    await asyncio.gather(*(s.serve_forever() for s in servers))


asyncio.run(main(sys.argv[1]))
