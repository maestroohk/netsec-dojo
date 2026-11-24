ip route add default via 10.18.1.254
mkdir -p /srv/nas
echo "<h1>Home NAS</h1><p>Photos, backups, media. Share code: $DOJO_FLAG</p>" > /srv/nas/index.html
cd /srv/nas && nohup python3 -m http.server 8080 >/dev/null 2>&1 &
