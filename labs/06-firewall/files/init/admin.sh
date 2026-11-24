ip route add default via 10.16.1.254
nohup python3 /lab/listen.py 9000 "admin file share" >/dev/null 2>&1 &
