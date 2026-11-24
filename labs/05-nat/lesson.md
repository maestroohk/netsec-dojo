# NAT and port forwarding

There are far more devices than IPv4 addresses. Your home has one public address from your ISP, yet every phone and laptop in the house gets online. The trick is **Network Address Translation**, done by your home router. In this lab you build it yourself.

## The network

```
 laptop 10.18.1.10 ─┐                                   
                    ├── router ──────────── website 203.0.113.80
 nas    10.18.1.20 ─┘  10.18.1.254 | 203.0.113.1     ("the internet")
        home 10.18.1.0/24                internet 203.0.113.0/24
```

## Private addresses

Three ranges are reserved for private networks and are never routed on the internet:

| Range | Typical use |
|---|---|
| `10.0.0.0/8` | companies, labs (all of this course) |
| `172.16.0.0/12` | Docker, some companies |
| `192.168.0.0/16` | home routers |

Millions of homes use `192.168.1.x` at the same time. That only works because those addresses never leave the house unchanged.

## Source NAT (masquerading)

When the laptop sends a packet out, the router rewrites the **source** address from `10.18.1.10` to its own public `203.0.113.1` and notes the connection in a table (conntrack). When the reply comes back to `203.0.113.1`, the router looks up the table and rewrites the **destination** back to `10.18.1.10`.

```
iptables -t nat -A POSTROUTING -s 10.18.1.0/24 ! -d 10.18.1.0/24 -j MASQUERADE
```

`MASQUERADE` means "use whatever address the outgoing interface has". It happens in `POSTROUTING` because the router must first decide which way the packet goes.

## Destination NAT (port forwarding)

The internet cannot start a connection to the laptop: `10.18.1.10` means nothing out there. To expose one service, you tell the router: "anything arriving at my public address on port 8080, send to the NAS".

```
iptables -t nat -A PREROUTING -d 203.0.113.1 -p tcp --dport 8080 \
         -j DNAT --to-destination 10.18.1.20:8080
```

This happens in `PREROUTING`, before routing, so the router then routes the rewritten packet inside.

Seeing NAT rules: `iptables -t nat -S` or `iptables -t nat -L -n -v`.

## Why a security person cares

- **NAT is not a firewall**, but it behaves a little like one: inside devices cannot be reached unless someone forwards a port. That is why a forgotten port forward (or UPnP adding one automatically) is a classic way a camera, NAS or game server ends up exposed on the internet.
- **Attribution**: logs on the website show only the router's address. Behind it could be one person or a whole company. Investigators need the router's NAT logs to go further.
- **Pivoting and tunnels**: attackers use the same ideas (forwarding a port through a compromised host) to reach networks they cannot route to directly.
