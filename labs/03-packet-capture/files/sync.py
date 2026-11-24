"""A report sync tool on the workstation: fetches a status page every few seconds over plain HTTP."""
import os
import time
import urllib.request

url = "http://10.13.2.10:%s/reports/status" % os.environ["DOJO_PORT"]
while True:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": os.environ["DOJO_AGENT"]})
        urllib.request.urlopen(req, timeout=3).read()
    except Exception:
        pass
    time.sleep(4)
