# Routers and static routes

In lab 1 two hosts shared one network. Real networks are many networks joined by **routers**. Here you connect a LAN to a DMZ through one router and learn the rule that trips up everyone at least once: **traffic needs a route there and a route back**.

## The network

```
 client                 router                  server
 10.12.1.10 ---- 10.12.1.254 | 10.12.2.254 ---- 10.12.2.10
        LAN 10.12.1.0/24          DMZ 10.12.2.0/24
```

The router has one interface in each network and forwarding is switched on. The client and the server each know only their own network.

## The routing table

Every host, not only routers, has a routing table. See it with:

```
ip route
```

Each line reads "to reach *this network*, send packets *this way*":

```
10.12.1.0/24 dev eth0 scope link      # my own network: deliver directly
default via 10.12.1.254 dev eth0      # everything else: hand to this router
```

For each packet the kernel picks the **most specific** matching line (longest prefix). `default` is shorthand for `0.0.0.0/0`, which matches everything and so is used only when nothing better matches. The router named after `via` is the **next hop**; it must be in a network the host is directly connected to.

```
ip route add default via 10.12.1.254          # a default gateway
ip route add 10.12.2.0/24 via 10.12.1.254     # or one specific network
ip route del default                          # remove
```

## A route back

A ping is two packets: a request and a reply. Each is routed independently by whichever host is holding it. If the client can send to the server but the server has no route to the client's network, the request arrives and the reply is dropped on the server. From the client it looks the same as the server being dead.

When something "doesn't respond", check the path in both directions.

## Seeing it

`tcpdump` shows packets as they pass an interface. On the router:

```
tcpdump -ni any icmp
```

`-n` skips name lookups, `-i any` listens on every interface. Run this while pinging and you can watch exactly how far the packets get.

`traceroute -n <address>` lists each router on the way to a destination.

## Why a security person cares

Routing decides what can talk to what. Network segmentation (keeping the database where the guest Wi-Fi cannot reach it) is routing plus firewalling (lab 7). When an attacker takes over one machine and uses it to reach networks they could not reach before, that is called **pivoting**, and it is this lesson seen from the other side.
