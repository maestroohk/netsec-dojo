# DNS: names to addresses

People use names (`intranet.dojo.lab`); packets need addresses (`10.14.1.50`). The **Domain Name System** translates between them. In this lab you query a DNS server by hand, read several kinds of record, and then make a PC use that server automatically.

## How a lookup works

1. A program asks the operating system for `intranet.dojo.lab`.
2. The OS checks `/etc/hosts`, then sends a query to the **resolver** listed in `/etc/resolv.conf`.
3. The resolver answers from its own data or asks other servers, and replies.

DNS normally runs over **UDP port 53**.

## Record types

| Type | Holds | Example |
|---|---|---|
| A | an IPv4 address | `intranet.dojo.lab → 10.14.1.50` |
| AAAA | an IPv6 address | |
| CNAME | an alias to another name | `www → web01.dojo.lab` |
| MX | the mail server for a domain, with a priority | `dojo.lab → 10 mail.dojo.lab` |
| TXT | free text | SPF/DKIM email policies, verification tokens |
| NS | which servers are authoritative for a zone | |
| PTR | reverse: address to name | |

## dig

```
dig @10.14.1.53 intranet.dojo.lab        # full answer from one server
dig @10.14.1.53 intranet.dojo.lab +short # just the data
dig @10.14.1.53 dojo.lab MX              # ask for a specific type
dig intranet.dojo.lab                    # use the resolver in /etc/resolv.conf
```

In full output, the **ANSWER SECTION** holds the records. `status: NXDOMAIN` means the name does not exist.

`getent hosts NAME` resolves a name the way ordinary programs do, so it is the test that matters for task 5.

## Why a security person cares

- **Reconnaissance**: DNS is often the first map of an organisation. Hostnames like `vault`, `vpn` or `backup` tell you what exists.
- **Leaks**: TXT records and forgotten names sometimes expose internal details.
- **Attacks on DNS**: whoever controls your resolver controls where your names point. Changing `/etc/resolv.conf` (task 5) is exactly what malware does to redirect a victim, and what DNS spoofing tries to achieve from the network.
- **Defence**: DNS logs are one of the best sources for spotting malware calling home.
