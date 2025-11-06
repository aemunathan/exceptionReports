#!/usr/bin/env python3
import csv, os, sys, time, requests, concurrent.futures, datetime

BASE_URL = os.environ.get("BITBUCKET_BASE_URL", "").rstrip("/")
PROJECT_KEY = os.environ.get("BITBUCKET_PROJECT_KEY", "")
TOKEN = os.environ.get("BITBUCKET_TOKEN")
USER = os.environ.get("BITBUCKET_USERNAME")
PWD = os.environ.get("BITBUCKET_PASSWORD")
VERIFY_SSL = os.environ.get("BITBUCKET_VERIFY_SSL", "true").lower() != "false"
MAX_WORKERS = int(os.environ.get("MAX_WORKERS", "12"))

if not BASE_URL or not PROJECT_KEY:
    sys.stderr.write("Please set BITBUCKET_BASE_URL and BITBUCKET_PROJECT_KEY.\n")
    sys.exit(1)

API = f"{BASE_URL}/rest/api/1.0"
UTC_NOW = datetime.datetime.now(datetime.timezone.utc)

session = requests.Session()
session.verify = VERIFY_SSL
if TOKEN:
    session.headers.update({"Authorization": f"Bearer {TOKEN}"})
elif USER and PWD:
    session.auth = (USER, PWD)
else:
    sys.stderr.write("Provide either BITBUCKET_TOKEN or BITBUCKET_USERNAME and BITBUCKET_PASSWORD.\n")
    sys.exit(1)

def backoff_get(url, **kwargs):
    for attempt in range(6):
        r = session.get(url, timeout=60, **kwargs)
        if r.status_code in (429,) or r.status_code >= 500:
            time.sleep(min(2 ** attempt, 30))
            continue
        r.raise_for_status()
        return r

def paged_get(url, params=None, limit=100):
    start = 0
    params = dict(params or {})
    params["limit"] = limit
    while True:
        params["start"] = start
        r = backoff_get(url, params=params)
        data = r.json()
        values = data.get("values", [])
        for v in values:
            yield v
        if data.get("isLastPage", False):
            return
        start = data.get("nextPageStart", start + len(values))

def get_repos(project_key):
    url = f"{API}/projects/{project_key}/repos"
    for repo in paged_get(url):
        yield {"slug": repo["slug"], "name": repo.get("name") or repo["slug"]}

def get_branches(project_key, repo_slug):
    url = f"{API}/projects/{project_key}/repos/{repo_slug}/branches"
    for br in paged_get(url):
        yield {
            "name": br.get("displayId") or br.get("id", "").split("/")[-1],
            "latestCommit": br.get("latestCommit"),
            "isDefault": br.get("isDefault", False),
        }

def iso_from_ms(ms):
    dt = datetime.datetime.fromtimestamp(ms / 1000.0, tz=datetime.timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")

def parse_iso(dt_str):
    """Return aware UTC datetime or None."""
    if not dt_str:
        return None
    try:
        if dt_str.endswith("Z"):
            return datetime.datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
        return datetime.datetime.fromisoformat(dt_str.replace("Z", "+00:00")).astimezone(datetime.timezone.utc)
    except Exception:
        return None

def days_since(dt_utc):
    if not dt_utc:
        return ""
    delta = UTC_NOW - dt_utc
    return str(max(0, int(delta.total_seconds() // 86400)))

def get_last_commit(project_key, repo_slug, branch_name, latest_commit_hash=None):
    """
    Try commits?until=<branch>&limit=1; fallback to /commits/{hash}.
    Returns dict: {hash, author_name, author_email, date_iso, date_dt}
    """
    url = f"{API}/projects/{project_key}/repos/{repo_slug}/commits"
    r = backoff_get(url, params={"until": branch_name, "limit": 1})
    vals = r.json().get("values", [])
    if vals:
        c = vals[0]
        author = c.get("author", {}) or {}
        name = author.get("name") or author.get("displayName") or ""
        email = author.get("emailAddress") or ""
        ts_ms = c.get("authorTimestamp")
        iso = iso_from_ms(ts_ms) if ts_ms is not None else (c.get("date") or "")
        dt = parse_iso(iso)
        return {"hash": c.get("id",""), "author_name": name, "author_email": email, "date_iso": iso, "date_dt": dt}

    if latest_commit_hash:
        url2 = f"{API}/projects/{project_key}/repos/{repo_slug}/commits/{latest_commit_hash}"
        r2 = backoff_get(url2)
        c = r2.json()
        author = c.get("author", {}) or {}
        return {
            "hash": c.get("id",""),
            "author_name": author.get("name",""),
            "author_email": author.get("emailAddress",""),
            "date_iso": "",
            "date_dt": None,
        }
    return {"hash": "", "author_name": "", "author_email": "", "date_iso": "", "date_dt": None}

def process_branch(project_key, repo, br):
    c = get_last_commit(project_key, repo["slug"], br["name"], br.get("latestCommit"))
    return [
        repo["name"],
        br["name"],
        c["hash"],
        c["author_name"],
        c["author_email"],
        c["date_iso"],
        days_since(c["date_dt"]),
        "yes" if br.get("isDefault") else "no",
    ]

def main():
    out_file = f"bitbucket_branches_{PROJECT_KEY}.csv"
    header = [
        "repo",
        "branch",
        "last_commit_hash",
        "last_commit_author",
        "last_commit_email",
        "last_commit_date_utc",
        "days_since_last_commit",
        "is_default_branch",
    ]
    rows = []
    for repo in get_repos(PROJECT_KEY):
        branches = list(get_branches(PROJECT_KEY, repo["slug"]))
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            futures = [ex.submit(process_branch, PROJECT_KEY, repo, br) for br in branches]
            for fut in concurrent.futures.as_completed(futures):
                rows.append(fut.result())

    # Sort newest first by date (blank dates go last)
    def sort_key(r):
        dt = parse_iso(r[5])  # ISO date column
        return (0, -dt.timestamp()) if dt else (1, 0)

    rows.sort(key=sort_key)

    with open(out_file, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"Wrote {out_file} with {len(rows)} rows.")

if __name__ == "__main__":
    main()
