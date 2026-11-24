# Build a private certificate authority and a server certificate signed by it.
set -e
mkdir -p /etc/shop /srv/pub
cd /etc/shop
openssl req -x509 -newkey rsa:2048 -nodes -days 3650 -subj "/CN=$DOJO_CA" \
  -keyout ca.key -out ca.crt 2>/dev/null
openssl req -newkey rsa:2048 -nodes -subj "/CN=shop.dojo.lab" \
  -keyout server.key -out server.csr 2>/dev/null
printf 'subjectAltName=DNS:shop.dojo.lab\nbasicConstraints=CA:FALSE\nextendedKeyUsage=serverAuth\n' > ext.cnf
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -days 365 \
  -extfile ext.cnf -out server.crt 2>/dev/null
cp ca.crt /srv/pub/ca.crt
cd /srv/pub && nohup python3 -m http.server 80 >/dev/null 2>&1 &
nohup python3 /lab/shop.py >/dev/null 2>&1 &
