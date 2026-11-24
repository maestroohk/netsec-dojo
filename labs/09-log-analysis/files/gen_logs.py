"""Generates a day of web and auth logs for the log analysis lab.

Background traffic from ordinary visitors, plus two incidents:
  - one address probing the web server for admin pages and backups
  - one address repeatedly failing SSH logins, then succeeding as one account
"""
import datetime as dt
import os
import random

rnd = random.Random(int(os.environ["DOJO_SEED"]))
SCANNER = os.environ["DOJO_SCANNER"]
GUESSER = os.environ["DOJO_GUESSER"]
USER = os.environ["DOJO_USER"]
day = dt.datetime(2026, 11, 20, 0, 0, 0)

visitors = ["10.17.1.%d" % n for n in rnd.sample(range(20, 70), 12)]
pages = ["/", "/", "/", "/about", "/products", "/products/42", "/contact", "/blog",
         "/blog/welcome", "/static/site.css", "/static/app.js", "/favicon.ico"]
agents = ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130.0",
          "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) Safari/605.1",
          "Mozilla/5.0 (X11; Linux x86_64; rv:131.0) Firefox/131.0"]
probes = ["/admin", "/admin.php", "/wp-login.php", "/wp-admin/", "/.env", "/.git/config",
          "/backup.zip", "/backup.sql", "/db.sql", "/phpmyadmin/", "/server-status", "/config.php",
          "/old/", "/test/", "/api/v1/users", "/login", "/console", "/actuator/health",
          "/.DS_Store", "/admin/login", "/manager/html", "/cgi-bin/test.cgi", "/debug", "/shell.php"]
found = {"/login": 200, "/api/v1/users": 401, "/server-status": 403}

web = []
for _ in range(rnd.randint(380, 460)):
    t = day + dt.timedelta(seconds=rnd.randint(0, 86399))
    page = rnd.choice(pages)
    status = 200 if rnd.random() > 0.03 else 404
    web.append((t, rnd.choice(visitors), "GET", page, status, rnd.randint(300, 9000), rnd.choice(agents)))

start = day + dt.timedelta(hours=rnd.randint(1, 5), minutes=rnd.randint(0, 59))
scan_list = probes * 3
rnd.shuffle(scan_list)
scan_list = scan_list[:rnd.randint(55, 72)]
if "/login" not in scan_list:
    scan_list[rnd.randint(10, len(scan_list) - 1)] = "/login"
for i, path in enumerate(scan_list):
    t = start + dt.timedelta(seconds=i * rnd.choice([1, 1, 2]))
    web.append((t, SCANNER, "GET", path, found.get(path, 404), rnd.randint(150, 600), "Mozilla/5.0 (compatible; Nmap Scripting Engine)"))

web.sort()
with open("/var/log/nginx/access.log", "w") as f:
    for t, ip, method, path, status, size, agent in web:
        f.write('%s - - [%s +0000] "%s %s HTTP/1.1" %d %d "-" "%s"\n'
                % (ip, t.strftime("%d/%b/%Y:%H:%M:%S"), method, path, status, size, agent))

auth = []
staff = [("deploy", "10.17.1.31"), ("maria", "10.17.1.44"), ("ops", "10.17.1.52")]
for _ in range(rnd.randint(14, 22)):
    t = day + dt.timedelta(seconds=rnd.randint(0, 86399))
    user, ip = rnd.choice(staff)
    pid = rnd.randint(1000, 30000)
    auth.append((t, pid, "Accepted publickey for %s from %s port %d ssh2" % (user, ip, rnd.randint(40000, 60000))))
    if rnd.random() < 0.2:
        auth.append((t - dt.timedelta(seconds=5), pid - 1, "Failed password for %s from %s port %d ssh2" % (user, ip, rnd.randint(40000, 60000))))

g_start = day + dt.timedelta(hours=rnd.randint(13, 20), minutes=rnd.randint(0, 59))
tries = ["root", "admin", "test", "oracle", "ubuntu", "postgres", "guest", "user", USER]
n = 0
for i in range(rnd.randint(40, 60)):
    name = rnd.choice(tries)
    t = g_start + dt.timedelta(seconds=n)
    n += rnd.choice([2, 3, 3, 4])
    if name == USER:
        auth.append((t, 40000 + i, "Failed password for %s from %s port %d ssh2" % (name, GUESSER, rnd.randint(40000, 60000))))
    else:
        auth.append((t, 40000 + i, "Failed password for invalid user %s from %s port %d ssh2" % (name, GUESSER, rnd.randint(40000, 60000))))
t = g_start + dt.timedelta(seconds=n + 3)
auth.append((t, 40999, "Accepted password for %s from %s port %d ssh2" % (USER, GUESSER, rnd.randint(40000, 60000))))
auth.append((t + dt.timedelta(seconds=1), 40999, "pam_unix(sshd:session): session opened for user %s(uid=1001) by (uid=0)" % USER))

auth.sort()
with open("/var/log/auth.log", "w") as f:
    for t, pid, msg in auth:
        f.write("%s webserver sshd[%d]: %s\n" % (t.strftime("%b %d %H:%M:%S"), pid, msg))
