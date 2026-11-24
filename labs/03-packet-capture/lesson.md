# Packet capture: reading the wire

Everything a network does is packets. A packet capture lets you stop guessing and look. In this lab you sit on a router, watch a workstation talk to a server, and read the conversation one layer at a time.

## Layers in one packet

A web request is a stack of envelopes:

| Layer | What it says | Example |
|---|---|---|
| Ethernet | which hardware (MAC) on this wire | `02:42:0a:0d:01:0a` |
| IP | which host, end to end | `10.13.1.10 > 10.13.2.10` |
| TCP | which program (port), and connection state | port `8443`, flags `[S]` |
| HTTP | what the program actually asked for | `GET /reports/status` |

tcpdump prints the IP and TCP layers on each line. With `-A` it also prints the payload, which is where HTTP lives.

## Ports

An IP address picks a host; a **port** (0–65535) picks a program on it. The server listens on a fixed port; the client uses a random high port for its side. So in `10.13.1.10.51234 > 10.13.2.10.8443`, the server port is `8443`.

## The TCP handshake

Before any data, TCP opens a connection with three packets:

```
client  -- [S]  SYN     -->  server    "I'd like to talk"
client  <-- [S.] SYN-ACK --  server    "OK, and I'd like to talk too"
client  -- [.]  ACK     -->  server    "Great"
```

tcpdump flag letters: `S` SYN, `.` ACK, `P` push (data), `F` FIN (close), `R` RST (reset/refused). A port scanner (lab 6) works by reading exactly these replies.

## Using tcpdump

```
tcpdump -ni any                    # everything, every interface, no name lookups
tcpdump -ni any host 10.13.2.10    # only traffic to/from one host
tcpdump -ni any port 80            # only one port
tcpdump -ni any -A port 80         # also print payloads as text
tcpdump -ni any -c 20 -w out.pcap  # save 20 packets to a file
tcpdump -nr out.pcap               # read a saved file
```

Filters combine with `and`, `or`, `not`: `tcp and src host 10.13.2.10`.

## Why a security person cares

The sync tool uses plain HTTP, so anyone on the path (this router, a compromised switch, a hostile Wi-Fi hotspot) can read every request and response in full. That is the whole reason **TLS (HTTPS)** exists: it encrypts the HTTP layer so a capture shows only addresses, ports and scrambled bytes. When you review a network, unencrypted protocols carrying sensitive data are a finding.

Captures are also the defender's ground truth. When an alert fires, a saved pcap shows exactly what was sent.
