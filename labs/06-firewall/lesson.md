# Firewalls with iptables

In lab 2 a router joined two networks and forwarded everything. Here you make it decide **what** may cross. You will build a small but realistic policy:

| From | To | Allowed |
|---|---|---|
| anyone on the LAN | web server (80) | yes |
| admin PC only | SSH (22) | yes |
| anyone | database (5432) | no |
| DMZ | LAN (new connections) | no |

## Chains

Linux's firewall (netfilter, driven by `iptables`) sorts packets into chains:

- `INPUT`: packets addressed **to** this machine
- `OUTPUT`: packets this machine sends
- `FORWARD`: packets passing **through** (the router's job)

Each chain is a list of rules checked top to bottom. The first rule that matches decides. If nothing matches, the chain's **policy** decides.

## Default deny

There are two ways to build a policy:

- **Default allow**: forward everything, add rules to block bad things. You will always forget something.
- **Default deny**: drop everything, add rules for what is needed. Forgetting something breaks a feature, which someone notices and reports, rather than leaving a hole nobody notices.

Use default deny.

## Stateful filtering

A connection has traffic in both directions. You only want to write rules for who may **start** a connection. The `conntrack` module remembers connections the firewall has already allowed, so one rule lets all their reply packets back:

```
iptables -A FORWARD -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
```

## Commands

```
iptables -S FORWARD                     # rules as commands
iptables -L FORWARD -n -v --line-numbers # rules as a table with packet counters
iptables -A FORWARD <match> -j ACCEPT   # append a rule
iptables -I FORWARD 1 <match> -j DROP   # insert at position 1
iptables -D FORWARD <line number>       # delete a rule
iptables -P FORWARD DROP                # set the policy
iptables -F FORWARD                     # flush (remove) all rules; does not reset the policy
```

Common matches: `-s 10.16.1.10` (source), `-d 10.16.2.10` (destination), `-p tcp --dport 80` (protocol and port).

The packet counters in `-L -v` are the best debugging tool you have: send a test connection and see which rule's counter went up.

> Setting `-P FORWARD DROP` before the allow rules cuts traffic immediately. On a real remote firewall, setting `INPUT` to DROP before allowing your own SSH session locks you out. Add allow rules first.

## Why a security person cares

Firewalls are where segmentation becomes real. The last rule, the DMZ not reaching in, is what limits damage when a public-facing server is compromised: the attacker gets the server, not the whole office. Reviewing firewall rules for overly broad allows (`-s 0.0.0.0/0` to a database port) is a routine part of an assessment.
