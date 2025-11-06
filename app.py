#!/usr/bin/env python3
import os, csv, io, time, datetime, concurrent.futures
from flask import Flask, request, render_template_string, send_file, abort
import requests

# ---------- Config (env) ----------
BASE_URL = os.environ.get("BITBUCKET_BASE_URL", "").rstrip("/")
TOKEN    = os.environ.get("BITBUCKET_TOKEN")
USER     = os.environ.get("BITBUCKET_USERNAME")
PWD      = os.environ.get("BITBUCKET_PASSWORD")
VERIFY_ENV = os.environ.get("BITBUCKET_VERIFY_SSL")  # "true"/"false" OR path to CA bundle
MAX_WORKERS = int(os.environ.get("MAX_WORKERS", "12"))

if not BASE_URL:
    raise SystemExit("Set BITBUCKET_BASE_URL")

def resolve_verify(v):
    if not v: return True
    lv = v.strip().lower()
    if lv in ("false","0","no","off"): return False
    if lv in ("true","1","yes","on"):  return True
    return v if os.path.exists(v) else True

VERIFY = resolve_verify(VERIFY_ENV)

session = requests.Session()
session.verify = VERIFY
if TOKEN:
    session.headers.update({"Authorization": f"Bearer {TOKEN}"})
elif USER and PWD:
    session.auth = (USER, PWD)
else:
    raise SystemExit("Provide BITBUCKET_TOKEN or BITBUCKET_USERNAME/PASSWORD")

if session.verify is False:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API = f"{BASE_URL}/rest/api/1.0"
RETRIABLE = {429, 500, 502, 503, 504}

# ---------- HTTP helpers ----------
def backoff_get(url, **kwargs):
    for attempt in range(6):
        try:
            r = session.get(url, timeout=60, **kwargs)
            if r.status_code in RETRIABLE:
                time.sleep(min(2 ** attempt, 30))
                continue
            if r.status_code >= 400:
                return None
            r.raise_for_status()
            return r
        except requests.RequestException:
            time.sleep(min(2 ** attempt, 30))
    return None

def paged_get(url, params=None, limit=100):
    start = 0
    params = dict(params or {})
    params["limit"] = limit
    while True:
        params["start"] = start
        r = backoff_get(url, params=params)
        if not r: return
        data = r.json()
        for v in data.get("values", []):
            yield v
        if data.get("isLastPage", False): return
        start = data.get("nextPageStart", start + len(data.get("values", [])))

# ---------- Bitbucket calls ----------
def get_repos(project_key):
    url = f"{API}/projects/{project_key}/repos"
    for repo in paged_get(url):
        yield {"slug": repo["slug"], "name": repo.get("name") or repo["slug"]}

def get_branches(project_key, repo_slug):
    url = f"{API}/projects/{project_key}/repos/{repo_slug}/branches"
    for br in paged_get(url):
        yield {
            "name": br.get("displayId") or br.get("id","").split("/")[-1],
            "latestCommit": br.get("latestCommit"),
            "isDefault": br.get("isDefault", False),
        }

def iso_from_ms(ms):
    dt = datetime.datetime.fromtimestamp(ms/1000.0, tz=datetime.timezone.utc)
    return dt.isoformat().replace("+00:00","Z")

def parse_iso(dt_str):
    if not dt_str: return None
    try:
        if dt_str.endswith("Z"):
            return datetime.datetime.strptime(dt_str,"%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
        return datetime.datetime.fromisoformat(dt_str.replace("Z","+00:00")).astimezone(datetime.timezone.utc)
    except Exception:
        return None

def get_last_commit(project_key, repo_slug, branch_name, latest_commit_hash=None):
    url = f"{API}/projects/{project_key}/repos/{repo_slug}/commits"
    r = backoff_get(url, params={"until": branch_name, "limit": 1})
    if r:
        vals = r.json().get("values", [])
        if vals:
            c = vals[0]
            author = c.get("author", {}) or {}
            name  = author.get("name") or author.get("displayName") or ""
            email = author.get("emailAddress") or ""
            ts_ms = c.get("authorTimestamp")
            iso   = iso_from_ms(ts_ms) if ts_ms is not None else (c.get("date") or "")
            dt    = parse_iso(iso)
            return {"hash": c.get("id",""), "author_name": name, "author_email": email, "date_iso": iso, "date_dt": dt}
    if latest_commit_hash:
        url2 = f"{API}/projects/{project_key}/repos/{repo_slug}/commits/{latest_commit_hash}"
        r2 = backoff_get(url2)
        if r2:
            c = r2.json()
            author = c.get("author", {}) or {}
            return {
                "hash": c.get("id",""),
                "author_name": author.get("name",""),
                "author_email": author.get("emailAddress",""),
                "date_iso": "",
                "date_dt": None,
            }
    return {"hash":"", "author_name":"", "author_email":"", "date_iso":"", "date_dt":None}

def days_since(dt_utc, now_utc):
    if not dt_utc: return ""
    delta = now_utc - dt_utc
    return max(0, int(delta.total_seconds()//86400))

# ---------- Data collection with filters ----------
# mode: "all" | "active" | "inactive"
def collect_rows(project_key, mode="all", since_days=None):
    now = datetime.datetime.now(datetime.timezone.utc)
    cutoff = None
    if since_days not in (None, ""):
        try:
            cutoff = now - datetime.timedelta(days=int(since_days))
        except Exception:
            cutoff = None

    def include(dt):
        if mode == "all" or cutoff is None:
            return True
        # ACTIVE => commits on/after cutoff
        if mode == "active":
            return (dt is not None) and (dt >= cutoff)
        # INACTIVE => commits before cutoff OR unknown date
        if mode == "inactive":
            return (dt is None) or (dt < cutoff)
        return True

    header = [
        "repo","branch","last_commit_hash","last_commit_author","last_commit_email",
        "last_commit_date_utc","days_since_last_commit","is_default_branch"
    ]
    rows = []

    for repo in get_repos(project_key):
        branches = list(get_branches(project_key, repo["slug"]))
        # parallel fetch tip commits
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            futs = {
                ex.submit(get_last_commit, project_key, repo["slug"], br["name"], br.get("latestCommit")): br
                for br in branches
            }
            for fut in concurrent.futures.as_completed(futs):
                br = futs[fut]
                c = fut.result()
                if not include(c["date_dt"]):
                    continue
                rows.append([
                    repo["name"],
                    br["name"],
                    c["hash"],
                    c["author_name"],
                    c["author_email"],
                    c["date_iso"],
                    days_since(c["date_dt"], now),
                    "yes" if br.get("isDefault") else "no",
                ])

    # newest first (blank dates last)
    def s_key(r):
        dt = parse_iso(r[5])
        return (0, -dt.timestamp()) if dt else (1, 0)
    rows.sort(key=s_key)
    return header, rows

# ---------- Flask UI ----------
app = Flask(__name__)

INDEX_HTML = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Bitbucket Branch Report</title>
<style>
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;max-width:780px;margin:40px auto;padding:0 16px;}
h1{font-size:1.6rem;margin-bottom:0.5rem}
form{display:grid; gap:12px; grid-template-columns:1fr 1fr; align-items:end}
label{display:block;font-weight:600;margin-bottom:6px}
input[type=text], input[type=number], select{width:100%; padding:8px; border:1px solid #ccc; border-radius:6px}
.row{grid-column:1/-1}
.btn{background:#1f6feb;color:#fff;border:none;padding:10px 14px;border-radius:8px;cursor:pointer}
.btn:hover{filter:brightness(0.95)}
.muted{color:#666;font-size:0.9rem}
</style>
</head>
<body>
  <h1>Bitbucket Branch Report</h1>
  <p class="muted">Server: <code>{{ base_url }}</code> · Auth: <code>{{ auth_mode }}</code></p>
  <form action="/download" method="get">
    <div>
      <label>Project Key</label>
      <input name="project" type="text" required placeholder="e.g., YOURPROJ" value="{{ default_project }}">
    </div>
    <div>
      <label>Format</label>
      <select name="format">
        <option value="csv" selected>CSV</option>
        <option value="json">JSON</option>
      </select>
    </div>
    <div>
      <label>Filter Mode</label>
      <select name="mode">
        <option value="all" selected>All branches</option>
        <option value="active">Active in last N days</option>
        <option value="inactive">Inactive (older than N days)</option>
      </select>
    </div>
    <div>
      <label>N days (for Active/Inactive)</label>
      <input name="since_days" type="number" min="0" placeholder="e.g., 90">
    </div>
    <div>
      <button class="btn" type="submit">Download</button>
    </div>
    <div class="row muted">
      Tip: Choose <em>All branches</em> and leave N blank to export everything, then filter on
      <code>days_since_last_commit</code> in Excel/Sheets.
    </div>
  </form>
</body>
</html>
"""

@app.route("/")
def index():
    auth_mode = "Token" if TOKEN else "Basic"
    return render_template_string(
        INDEX_HTML,
        base_url=BASE_URL,
        auth_mode=auth_mode,
        default_project=request.args.get("project","")
    )

@app.route("/download")
def download():
    project = (request.args.get("project") or "").strip()
    if not project: abort(400, "Missing project key")
    fmt  = (request.args.get("format") or "csv").lower()
    mode = (request.args.get("mode") or "all").lower()
    since_days = request.args.get("since_days")
    since_days = since_days if since_days not in (None,"") else None

    header, rows = collect_rows(project, mode=mode, since_days=since_days)

    if fmt == "json":
        import json
        payload = [
            dict(zip(header, r))
            for r in rows
        ]
        buf = io.BytesIO(json.dumps(payload, indent=2).encode("utf-8"))
        return send_file(buf, mimetype="application/json", as_attachment=True,
                         download_name=f"bitbucket_branches_{project}.json")

    # CSV
    s = io.StringIO()
    w = csv.writer(s)
    w.writerow(header); w.writerows(rows)
    return send_file(io.BytesIO(s.getvalue().encode("utf-8")),
                     mimetype="text/csv", as_attachment=True,
                     download_name=f"bitbucket_branches_{project}.csv")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT","8080")))
