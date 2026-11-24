# Log analysis: spotting an incident

Attacks leave traces. Most of a defender's day is reading logs to tell the boring majority from the few lines that matter. In this lab you investigate a web server's day using nothing but standard Linux text tools.

## The logs

**Web access log** (`/var/log/nginx/access.log`), one line per request:

```
10.17.1.31 - - [20/Nov/2026:09:14:02 +0000] "GET /products HTTP/1.1" 200 4312 "-" "Mozilla/5.0 ..."
```

Split on spaces, the useful fields are:

| Field | Meaning |
|---|---|
| `$1` | client IP |
| `$4` | time |
| `$6` `$7` | method and path (`"GET`, `/products`) |
| `$9` | status code |
| `$10` | response size |

Status codes: `200` OK, `301/302` redirect, `401` needs login, `403` forbidden, `404` not found, `500` server error.

**SSH auth log** (`/var/log/auth.log`):

```
Nov 20 15:02:11 webserver sshd[40012]: Failed password for invalid user admin from 185.12.3.4 port 51234 ssh2
Nov 20 15:04:40 webserver sshd[40999]: Accepted password for backup from 185.12.3.4 port 50001 ssh2
```

`invalid user` means the account does not exist; a plain `Failed password for X` means it does.

## The toolkit

```
wc -l file                         # count lines
grep 'text' file                   # lines containing text
grep -v 'text' file                # lines NOT containing text
grep -o 'from [0-9.]*' file        # print only the matching part
awk '{print $1}' file              # print field 1
awk '$9 == 404 {print $1}' file    # print field 1 where field 9 is 404
sort | uniq -c | sort -rn | head   # count identical lines, most frequent first
```

That last pipeline is the most useful line in log analysis. "Which IP made the most requests?":

```
awk '{print $1}' access.log | sort | uniq -c | sort -rn | head
```

## Patterns to recognise

- **Path scanning**: one address, many different paths, mostly 404, seconds apart, often a tool's User-Agent. Paths like `/.env`, `/.git/config`, `/backup.sql`, `/wp-login.php` are scanners looking for common mistakes.
- **Password guessing**: one address, many `Failed password` lines, many usernames. Dangerous the moment it is followed by `Accepted` from the same address.
- **Normal noise**: a few 404s from real visitors (typos, old links) are fine.

## Why a security person cares

This is the core loop of a security operations centre: notice an anomaly, scope it (what did they touch?), contain it (block, disable account), then fix the root cause. Tools like SIEMs (Splunk, Elastic, Sentinel) do the same counting and filtering at scale, and the queries are the same ideas as the pipelines above.
