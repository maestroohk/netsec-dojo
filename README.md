# netsec-dojo

Hands-on networking and security labs that run on your own machine. Each lab is a short lesson plus a small network of containers (PCs, routers, servers) that you log into and work on. Tasks are checked automatically.

## Requirements

- Docker Desktop, running (WSL2 backend)
- Python 3.10+ (standard library only, nothing to install)

## Start

From this folder:

```
python dojo.py setup     # builds the lab tools image once (a few minutes)
python dojo.py serve     # opens the course page at http://127.0.0.1:8377
```

On Windows, `dojo` (via `dojo.cmd`) works in place of `python dojo.py`.

In the page: pick a lab, read the **Lesson**, press **Start lab**, open a terminal from **Hosts**, and work through **Tasks**. Use **Hint** before **Show solution**.

## Command line

Everything in the page also works from a terminal:

```
dojo list                     # labs and progress
dojo start 1                  # start lab 1 (restarting resets it)
dojo shell 1 pc2              # shell on host pc2 of lab 1
dojo tasks 1                  # read the tasks
dojo answer 1 t2 62           # answer a question task
dojo check 1                  # check the hands-on tasks
dojo hint 1 t4                # first hint; add -n 2 for the next
dojo stop --all               # stop every running lab
```

Stop labs when you finish. Each lab uses only a few small containers, but there is no reason to leave them running.

## Curriculum

| # | Lab | You learn |
|---|---|---|
| 1 | IP addresses, subnets and ping | prefixes, subnet maths, ARP |
| 2 | Routers and static routes | routing tables, gateways, the route back, traceroute |
| 3 | Packet capture | tcpdump, ports, TCP handshake, why plain HTTP is readable |
| 4 | DNS | dig, record types, resolvers |
| 5 | Port scanning with nmap | host discovery, open/closed/filtered, banners |
| 6 | Firewalls with iptables | default deny, stateful rules, segmentation |
| 7 | Log analysis | grep/awk/sort pipelines, spotting scans and break-ins, containment |

Answers such as flags, ports and addresses are randomised each time a lab starts, so you cannot copy them from a previous run.

### Where to go next

These labs cover the foundations. For offensive web and exploitation practice, use platforms built and moderated for it:

- [PortSwigger Web Security Academy](https://portswigger.net/web-security) (free): SQL injection, XSS, authentication flaws
- [OverTheWire Bandit](https://overthewire.org/wargames/bandit/) (free): Linux and command line
- [TryHackMe](https://tryhackme.com) / [Hack The Box](https://www.hackthebox.com): guided rooms and machines

## Writing a lab

A lab is a folder in `labs/`:

```
labs/08-my-lab/
  lab.json             title, hosts, tasks, hints, solutions, random variables
  lesson.md            the lesson text (simple Markdown)
  docker-compose.yml   the network; every host uses image dojo-toolbox:latest
  files/               mounted read-only at /lab on every host
  files/init/<host>.sh runs once when <host> starts
```

Task types in `lab.json`:

- `answer`: compared with `answer` (a string or list), or with the output of `answer_cmd` run inside a host.
- `state`: passes when every command in `checks` succeeds (or fails, with `"expect": "fail"`).

`vars` define per-run random values (`flag`, `int`, `choice`, `ip`). Use them as `{{NAME}}` in task text, answers and commands, and as `${DOJO_NAME}` in `docker-compose.yml`.

Every task should have a `solution` (`steps` to run, and/or an `answer_cmd`). Then:

```
dojo selftest 8
```

starts the lab, checks that no hands-on task passes before you do anything, runs each solution, and checks that every task then passes.

Hosts lose their default route at boot (see `images/toolbox/node-init`), so labs cannot reach the internet unless you set `NODE_KEEP_DEFAULT_ROUTE=1`.
