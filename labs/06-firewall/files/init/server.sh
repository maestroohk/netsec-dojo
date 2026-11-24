ip route add default via 10.16.2.254
nohup python3 /lab/listen.py 22 "SSH-2.0-OpenSSH_9.2p1 Debian-2" >/dev/null 2>&1 &
nohup python3 /lab/listen.py 5432 "postgres" >/dev/null 2>&1 &
mkdir -p /srv/www && echo "<h1>Company web site</h1>" > /srv/www/index.html
cd /srv/www && nohup python3 -m http.server 80 >/dev/null 2>&1 &
