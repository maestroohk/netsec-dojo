mkdir -p /srv/www
echo "<h1>Intranet</h1><p>You routed your way here. Flag: $DOJO_FLAG</p>" > /srv/www/index.html
cd /srv/www && nohup python3 -m http.server 80 >/dev/null 2>&1 &
