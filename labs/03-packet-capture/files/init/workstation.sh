ip route add default via 10.13.1.254
nohup python3 /lab/sync.py >/dev/null 2>&1 &
