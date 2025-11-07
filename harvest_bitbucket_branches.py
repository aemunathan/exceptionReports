#!/usr/bin/env python3
import argparse, asyncio, aiohttp, async_timeout, time, os, sys, csv, json, signal
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple

RETRIABLE = {429, 500, 502, 503, 504}

def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def iso_from_ms(ms: Optional[int]) -> str:
    if ms is None: return ""
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc).isoformat().replace("+00:00","Z")

def days_since_iso(iso_str: str) -> str:
    if not iso_str: return ""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z","+00:00"))
        delta = datetime.now(timezone.utc) - dt
        d = int(delta.total_seconds() // 86400)
        return str(max(0, d))
    except Exception:
        return ""

class RateLimiter:
    """Simple token bucket limiter for requests/second."""
    def __init__(self, rps: float):
        self.rps = max(0.1, rps)
        self._last = 0.0

    async def wait(self):
        now = time.perf_counter()
        min_interval = 1.0 / self.rps
        elapsed = now - self._last
        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)
        self._last = time.perf_counter()

async def backoff_get(session: aiohttp.ClientSession, url: str, params=None, timeout_s=60, retries=6, limiter: Optional[RateLimiter]=None):
    for attempt in range(retries):
        if limiter: await limiter.wait()
        try:
            with async_timeout.timeout(timeout_s):
                async with session.get(url, params=params) as resp:
                    # Retriable
                    if resp.status in RETRIABLE:
                        await asyncio.sleep(min(2**attempt, 30))
                        continue
                    if resp.status >= 400:
                        # Non-retriable client errors: swallow with None
                        return None
                    return await resp.json()
        except (aiohttp.ClientError, asyncio.TimeoutError):
            await asyncio.sleep(min(2**attempt, 30))
    return None

async def paged_get(session, base_url, params=None, limit=100, timeout_s=60, limiter=None):
    """Generator yielding values across Bitbucket Server paged endpoints."""
    start = 0
    while True:
        q = dict(params or {})
        q.update({"limit": limit, "start": start})
        data = await backoff_get(session, base_url, params=q, timeout_s=timeout_s, limiter=limiter)
        if not data:
            return
        values = data.get("values", [])
        for v in values:
            yield v
        if data.get("isLastPage", False):
            return
        start = data.get("nextPageStart", start + len(values))

async def get_repos(session, api_base, project_key, limiter):
    url = f"{api_base}/projects/{project_key}/repos"
    async for repo in paged_get(session, url, limiter=limiter):
        yield {
            "slug": repo["slug"],
            "name": repo.get("name") or repo["slug"],
            "project_key": project_key,
            "state": repo.get("state", "AVAILABLE")
        }

async def get_branches(session, api_base, project_key, repo_slug, limiter):
    url = f"{api_base}/projects/{project_key}/repos/{repo_slug}/branches"
    async for br in paged_get(session, url, limiter=limiter):
        yield {
            "name": br.get("displayId") or (br.get("id","").split("/")[-1]),
            "latestCommit": br.get("latestCommit"),
            "isDefault": br.get("isDefault", False)
        }

async def get_tip_commit(session, api_base, project_key, repo_slug, branch_name, latest_hash, limiter):
    # primary: commits?until=<branch>&limit=1
    url = f"{api_base}/projects/{project_key}/repos/{repo_slug}/commits"
    data = await backoff_get(session, url, params={"until": branch_name, "limit": 1}, limiter=limiter)
    if data and data.get("values"):
        c = data["values"][0]
        author = c.get("author", {}) or {}
        ts_iso = iso_from_ms(c.get("authorTimestamp"))
        return {
            "hash": c.get("id",""),
            "author_name": author.get("name") or author.get("displayName") or "",
            "author_email": author.get("emailAddress") or "",
            "date_iso": ts_iso
        }
    # fallback by hash
    if latest_hash:
        url2 = f"{api_base}/projects/{project_key}/repos/{repo_slug}/commits/{latest_hash}"
        c = await backoff_get(session, url2, limiter=limiter)
        if c:
            author = c.get("author", {}) or {}
            return {
                "hash": c.get("id",""),
                "author_name": author.get("name",""),
                "author_email": author.get("emailAddress",""),
                "date_iso": ""
            }
    return {"hash":"", "author_name":"", "author_email":"", "date_iso":""}

def make_row(project_key, repo_name, repo_slug, br, tip) -> Dict[str,Any]:
    iso = tip.get("date_iso","")
    return {
        "project_key": project_key,
        "repo": repo_name,
        "repo_slug": repo_slug,
        "branch": br["name"],
        "last_commit_hash": tip.get("hash",""),
        "last_commit_author": tip.get("author_name",""),
        "last_commit_email": tip.get("author_email",""),
        "last_commit_date_utc": iso,
        "days_since_last_commit": days_since_iso(iso),
        "is_default_branch": "yes" if br.get("isDefault") else "no"
    }

def make_empty_repo_record(project_key, repo_name, repo_slug):
    return {
        "project_key": project_key,
        "repo": repo_name,
        "repo_slug": repo_slug,
        "branch": "",
        "last_commit_hash": "",
        "last_commit_author": "",
        "last_commit_email": "",
        "last_commit_date_utc": "",
        "days_since_last_commit": "",
        "is_default_branch": "no",
        "has_branches": "no"
    }

async def process_repo(session, api_base, project_key, repo, sem, limiter, ndjson_fh, csv_writer, resume_fh):
    async with sem:
        repo_name = repo["name"]; slug = repo["slug"]
        # branches
        branches = [br async for br in get_branches(session, api_base, project_key, slug, limiter)]
        if not branches:
            rec = make_empty_repo_record(project_key, repo_name, slug)
            ndjson_fh.write(json.dumps(rec) + "\n"); ndjson_fh.flush()
            if csv_writer:
                csv_writer.writerow([rec.get(k,"") for k in CSV_HEADER])
            if resume_fh:
                resume_fh.write(f"{project_key}/{slug}\n"); resume_fh.flush()
            return 1

        # per-branch tip commit (bounded concurrency inside repo)
        inner_sem = asyncio.Semaphore(16)  # per-repo throttle
        async def one(br):
            async with inner_sem:
                tip = await get_tip_commit(session, api_base, project_key, slug, br["name"], br.get("latestCommit"), limiter)
                row = make_row(project_key, repo_name, slug, br, tip)
                ndjson_fh.write(json.dumps(row) + "\n")
                if csv_writer:
                    csv_writer.writerow([row.get(k,"") for k in CSV_HEADER])
        await asyncio.gather(*[one(br) for br in branches])

        ndjson_fh.flush()
        if resume_fh:
            resume_fh.write(f"{project_key}/{slug}\n"); resume_fh.flush()
        return len(branches)

CSV_HEADER = [
    "project_key","repo","repo_slug","branch",
    "last_commit_hash","last_commit_author","last_commit_email",
    "last_commit_date_utc","days_since_last_commit","is_default_branch"
]

async def main_async(args):
    # SSL verify
    ssl_verify = True
    if args.verify_ssl.lower() in ("false","0","no","off"):
        ssl_verify = False
    elif args.verify_ssl.lower() in ("true","1","yes","on"):
        ssl_verify = True
    else:
        # path
        if os.path.isfile(args.verify_ssl):
            ssl_verify = args.verify_ssl
        # else keep default True

    timeout = aiohttp.ClientTimeout(total=None, connect=30, sock_read=90)
    connector = aiohttp.TCPConnector(limit= args.max_concurrent * 2, ssl=None if ssl_verify is True else None)
    headers = {}
    auth = None
    if args.token:
        headers["Authorization"] = f"Bearer {args.token}"
    elif args.username and args.password:
        auth = aiohttp.BasicAuth(args.username, args.password)
    else:
        print("Provide either --token or --username/--password", file=sys.stderr); return 2

    if not args.base_url.endswith("/rest/api/1.0"):
        api_base = args.base_url.rstrip("/") + "/rest/api/1.0"
    else:
        api_base = args.base_url.rstrip("/")

    # warning suppression for unverified HTTPS
    if not ssl_verify:
        import warnings
        from aiohttp import client_exceptions
        warnings.filterwarnings("ignore", category=UserWarning)

    limiter = RateLimiter(args.rps)
    sem = asyncio.Semaphore(args.max_concurrent)

    # resume set
    already = set()
    if args.resume_file and os.path.isfile(args.resume_file):
        with open(args.resume_file,"r") as rf:
            already = {line.strip() for line in rf if line.strip()}

    # open outputs
    ndjson_fh = open(args.out_ndjson, "a", encoding="utf-8")
    csv_fh = open(args.out_csv, "a", newline="", encoding="utf-8") if args.out_csv else None
    csv_writer = None
    if csv_fh:
        if os.stat(args.out_csv).st_size == 0:
            csv_writer = csv.writer(csv_fh); csv_writer.writerow(CSV_HEADER)
        else:
            csv_writer = csv.writer(csv_fh)

    resume_fh = open(args.resume_file, "a", encoding="utf-8") if args.resume_file else None

    # graceful shutdown handling
    stop = False
    def handle_sig(*_):
        nonlocal stop
        stop = True
        print("\n⛔ received stop signal; finishing in-flight tasks...", file=sys.stderr)
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, handle_sig)
        except Exception:
            pass

    async with aiohttp.ClientSession(
        headers=headers, auth=auth, timeout=timeout, connector=connector, trust_env=True
    ) as session:
        # apply SSL verify settings
        session._default_ssl = None  # allow per-session default
        # iterate project keys
        with open(args.project_file, "r") as pf:
            projects = [line.strip() for line in pf if line.strip() and not line.strip().startswith("#")]

        tasks = []
        total_branches = 0
        started = time.time()

        for pkey in projects:
            if stop: break
            # enumerate repos
            async for repo in get_repos(session, api_base, pkey, limiter):
                key = f"{pkey}/{repo['slug']}"
                if key in already:
                    continue
                if stop: break
                t = asyncio.create_task(process_repo(session, api_base, pkey, repo, sem, limiter, ndjson_fh, csv_writer, resume_fh))
                tasks.append(t)
                # optional backpressure
                if len(tasks) - sum(1 for t in tasks if t.done()) > args.max_concurrent * 4:
                    # wait for some to finish
                    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                    for d in done:
                        try:
                            total_branches += d.result() or 0
                        except Exception:
                            pass
                    tasks = list(pending)

        # drain
        if tasks:
            for t in asyncio.as_completed(tasks):
                try:
                    total_branches += await t or 0
                except Exception:
                    pass

        elapsed = time.time() - started
        print(f"Done. Projects: {len(projects)} | Elapsed: {elapsed:.1f}s", file=sys.stderr)

    ndjson_fh.close()
    if csv_fh: csv_fh.close()
    if resume_fh: resume_fh.close()
    return 0

def parse_args():
    ap = argparse.ArgumentParser(description="Harvest Bitbucket Server/DC branches + tip commit at scale")
    ap.add_argument("--base-url", required=True, help="Bitbucket base (e.g., https://bitbucket.company.com)")
    ap.add_argument("--token", help="Personal Access Token")
    ap.add_argument("--username", help="Username (if no token)")
    ap.add_argument("--password", help="Password (if no token)")
    ap.add_argument("--verify-ssl", default="true", help='"true" | "false" | /path/to/ca-bundle.crt')
    ap.add_argument("--project-file", required=True, help="Text file with one PROJECT_KEY per line")
    ap.add_argument("--out-ndjson", default="branches.ndjson", help="Append NDJSON output here")
    ap.add_argument("--out-csv", default="branches.csv", help="Append CSV output here")
    ap.add_argument("--resume-file", default="harvest_resume.txt", help="Track completed repos for resume")
    ap.add_argument("--max-concurrent", type=int, default=32, help="Concurrent repos in flight")
    ap.add_argument("--rps", type=float, default=10.0, help="Global requests per second cap")
    return ap.parse_args()

def main():
    args = parse_args()
    rc = asyncio.run(main_async(args))
    sys.exit(rc)

if __name__ == "__main__":
    main()
