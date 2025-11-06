#!/usr/bin/env python3
"""
Bitbucket Server/DC: list all branches for every repo in a project,
including tip commit author/date and days since last commit.

Outputs: bitbucket_branches_<PROJECT_KEY>.csv
"""

import csv
import datetime
import os
import sys
import time
import concurrent.futures
import requests

# ----------------------------
# Env / Config
# ----------------------------
BASE_URL = os.environ.get("BITBUCKET_BASE_URL", "").rstrip("/")
PROJECT_KEY = os.environ.get("BITBUCKET_PROJECT_KEY", "")
TOKEN = os.environ.get("BITBUCKET_TOKEN")
USER = os.environ.get("BITBUCKET_USERNAME")
PWD = os.environ.get("BITBUCKET_PASSWORD")
VERIFY_ENV = os.environ.get("BITBUCKET_VERIFY_SSL")  # "true"/"false" or path to CA bundle
MAX_WORKERS = int(os.environ.get("MAX_WORKERS", "12"))

if not BASE_URL or not PROJECT_KEY:
    sys.stderr.write("Please set BITBUCKET_BASE_URL and BITBUCKET_PROJECT_KEY.\n")
    sys.exit(1)

API = f"{BASE_URL}/rest/api/1.0"
UTC_NOW = datetime.datetime.now(datetime.timezone.utc)

# ----------------------------
# SSL verify resolution (+ optional warning suppression)
# ----------------------------
def resolve_verify(v):
    if v is None or v == "":
        return True
    lv = v.strip().lower()
    if lv in ("false", "0", "no", "off"):
        return False
    if lv in ("true", "1", "yes", "on"):
        return True
    # treat as path to CA bundle
    return v if os.path.exists(v) else True

VERIFY = resolve_verify(VERIFY_ENV)

session = requests.Session()
session.verify = VERIFY
if TOKEN:
    session.headers.update({"Authorization": f"Bearer {TOKEN}"})
elif USER and PWD:
    session.auth = (USER, PWD)
else:
    sys.stderr.write("Provide either BITBUCKET_TOKEN or BITBUCKET_USERNAME and BITBUCKET_PASSWORD.\n")
    sys.exit(1)

# If verification is disabled, suppress noisy warnings
if session.verify is False:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ----------------------------
# HTTP helpers (robust + retries)
# ----------------------------
RETRIABLE = {429, 500, 502, 503, 504}

def backoff_get(url, **kwargs):
    for attempt in range(6):
        try:
            r = session.get(url, timeout=60, **kwargs)
            if r.status_code in RETRIABLE:
                # exponential backoff up to ~30s
                time.sleep(min(2 ** attempt, 30))
                continue
            if r.status_code >= 400:
                # Non-retriable error: log and return None
                print(f"⚠️  HTTP {r.status_code} {r.reason} for {url}")
                return None
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            print(f"⚠️  Request error ({e}); retrying...")
            time.sleep(min(2 ** attempt, 30))
    print(f"❌  Failed after retries: {url}")
    return None

def paged_get(url, params=None, limit=100):
    start = 0
    params = dict(params or {})
    params["limit"] = limit
    while True:
        params["start"] = start
        r = backoff_get(url, params=params)
        if not r:
            return  # stop paging on failure
        data = r.json()
        values = data.get("values", [])
        for v in values:
            yi
