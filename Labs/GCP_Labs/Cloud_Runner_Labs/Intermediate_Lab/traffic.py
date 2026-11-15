"""Sends a burst of complaints to the Cloud Run service so Logs and Metrics have something to show.

Usage: python traffic.py <service_url> [number_of_requests]   (default 300)
"""
import random
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

# BigQuery caches repeated queries for 24h, so reusing these ZIPs keeps the scan cost near zero
ZIPS = ["10001", "10002", "10003", "10011", "10025", "10027", "10031", "10301", "10314", "10451",
        "10458", "11201", "11211", "11215", "11222", "11237", "11354", "11368", "11375", "11432"]
BAD = ["90210", "1000a", ""]  # a 404 and two 400s so the error graphs aren't empty


def send(_):
    path = random.choices(["/complain", "/wall-of-complaints", "/"], weights=[8, 1, 1])[0]
    zip_code = random.choice(ZIPS * 5 + BAD)
    try:
        with urllib.request.urlopen(f"{URL}{path}?zip={zip_code}", timeout=60) as r:
            code = r.status
    except urllib.error.HTTPError as e:
        code = e.code
    except Exception as e:
        code = type(e).__name__
    print(code, path, zip_code or "(empty)")
    time.sleep(random.uniform(0, 2))
    return code


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    URL = sys.argv[1].rstrip("/")
    total = int(sys.argv[2]) if len(sys.argv) > 2 else 300
    with ThreadPoolExecutor(max_workers=10) as pool:
        print(Counter(pool.map(send, range(total))))
