# IP addresses, subnets and ping

Every device on a network needs an address. In this lab you read addresses, work out which network they belong to, and repair a PC that was given the wrong one.

## The idea

An IPv4 address is 32 bits, written as four numbers from 0 to 255: `10.11.1.10`.

An address on its own is only half the story. The **prefix length** (the `/24`) says how many of the leading bits name the **network**. The remaining bits name the **host** inside that network.

| Written | Network bits | Host bits | Addresses | Usable hosts |
|---|---|---|---|---|
| `/24` | 24 | 8 | 256 | 254 |
| `/25` | 25 | 7 | 128 | 126 |
| `/26` | 26 | 6 | 64 | 62 |
| `/30` | 30 | 2 | 4 | 2 |

Two addresses in each network are reserved: the first (the **network address**, host bits all 0) and the last (the **broadcast address**, host bits all 1). That is why usable hosts = 2^(host bits) − 2.

For `10.11.1.10/24`:

- network address: `10.11.1.0`
- usable hosts: `10.11.1.1` to `10.11.1.254`
- broadcast: `10.11.1.255`

## Why the prefix matters

When a host wants to send a packet, it asks one question: **is the destination in my own network?**

- **Yes**: deliver it directly over the local wire.
- **No**: hand it to a router (lab 2). With no router configured, the host gives up at once with `Network is unreachable`.

So two machines plugged into the same switch still cannot talk if their addresses put them in different networks. That is the fault in this lab.

## ARP: from IP address to hardware address

On the local wire, frames are delivered to **MAC addresses** (like `02:42:0a:0b:01:14`), not IP addresses. Before the first packet, the sender broadcasts an **ARP** request: "who has 10.11.1.20?" The owner replies with its MAC, and the sender caches it in its **neighbour table**.

## Commands for this lab

```
ip -br addr                      # brief list of interfaces and addresses
ip addr add 10.0.0.5/24 dev eth0 # add an address
ip addr del 10.0.0.5/24 dev eth0 # remove an address
ping -c 2 10.0.0.1               # send 2 echo requests
ip neigh                         # the ARP / neighbour table
```

## Why a security person cares

Almost every attack and every defence starts with "which hosts can reach which?" Reading addresses and prefixes fluently is how you answer that. ARP also has no authentication at all, which is what makes ARP spoofing possible.

Start the lab, open a shell on `pc1`, and work through the tasks.
