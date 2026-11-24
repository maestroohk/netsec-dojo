# Port scanning with nmap

Before you can defend or test a network you need a map: which hosts exist and which services they expose. **nmap** is the standard tool for building that map.

> Only scan networks you own or have written permission to test. Scanning other people's systems can be illegal. Everything in this lab is inside containers on your machine.

## How a scan works

nmap uses the TCP handshake from lab 3. To test a port it sends a SYN and reads the reply:

| Reply | Meaning | nmap says |
|---|---|---|
| SYN-ACK | something is listening | `open` |
| RST | host is up, nothing listening | `closed` |
| nothing | a firewall dropped it | `filtered` |

Host discovery (`-sn`) skips ports and just checks which addresses answer at all. On a local network it uses ARP, which is fast and hard to block.

## Commands

```
nmap -sn 10.15.1.0/24              # which hosts are up?
nmap 10.15.1.20                    # top 1,000 TCP ports
nmap -p 80 --open 10.15.1.0/24     # one port across a range, only show open
nmap -p- -T4 10.15.1.20            # all 65,535 ports, faster timing
nmap -sV -p 21,80 10.15.1.20       # identify service versions
nmap -n ...                        # skip DNS lookups (faster, quieter)
```

To talk to a service by hand:

```
nc 10.15.1.20 21                   # open a raw TCP connection; Ctrl+C to quit
```

## Ports worth recognising

| Port | Service |
|---|---|
| 21 | FTP |
| 22 | SSH |
| 25 | SMTP (mail) |
| 53 | DNS |
| 80 / 443 | HTTP / HTTPS |
| 445 | SMB (Windows file sharing) |
| 3306 | MySQL |
| 3389 | RDP (Windows remote desktop) |
| 5432 | PostgreSQL |

## Why a security person cares

- **Attack surface**: every open port is a program that strangers can talk to. A defender's first job is knowing that list and closing what is not needed.
- **Hidden services**: admins move services to odd ports thinking it hides them. A full `-p-` scan finds them in seconds.
- **Versions**: a banner like `ProFTPD 1.3.5` can be looked up in vulnerability databases (that version has a well-known critical flaw). Hiding banners does not fix bugs, but leaving them makes an attacker's job easy.
- **Detection**: scans are noisy. Lab 9 looks at what they leave in logs.
