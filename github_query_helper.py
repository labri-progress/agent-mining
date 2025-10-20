# github_global_scan.py (rate-limit aware)
import os
import time
import requests
import sys
from datetime import datetime
from typing import Optional, Dict, Any, List, Set

from heuristic import Heuristic, _match_pattern

GITHUB_API = "https://api.github.com"
# --- Add these near the top of github_global_scan.py ---

RATE_LIMIT_LOGGING = True  # default on


def set_rate_limit_logging(on: bool):
    global RATE_LIMIT_LOGGING
    RATE_LIMIT_LOGGING = bool(on)


def _print_once(line: str):
    if RATE_LIMIT_LOGGING:
        print(line, flush=True)


def _countdown(wait_seconds: int, *, label: str, end_ts: int | None = None):
    """Text progress bar with ETA; updates ~1s."""
    if not RATE_LIMIT_LOGGING or wait_seconds <= 0:
        time.sleep(max(0, wait_seconds))
        return
    total = int(wait_seconds)
    start = time.time()
    width = 30  # bar width
    while True:
        now = time.time()
        elapsed = int(now - start)
        remaining = max(0, total - elapsed)
        # When we know the reset timestamp, prefer that for accuracy
        if end_ts:
            remaining = max(0, int(end_ts - now))

        filled = int(((total - remaining) / max(1, total)) * width)
        bar = "█" * filled + "░" * (width - filled)
        mm, ss = divmod(remaining, 60)
        sys.stdout.write(f"\r[{bar}] {label} — resumes in {mm:02d}:{ss:02d}")
        sys.stdout.flush()
        if remaining <= 0:
            break
        time.sleep(1)
    sys.stdout.write("\n")
    sys.stdout.flush()


# ---------- Utility


def _auth_headers(
    token: Optional[str], *, accept: Optional[str] = None
) -> Dict[str, str]:
    headers = {
        "User-Agent": "global-heuristic-scanner/1.0",
        "Accept": accept or "application/vnd.github+json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _parse_link_header(link_header: str) -> Dict[str, str]:
    links = {}
    if not link_header:
        return links
    for part in link_header.split(","):
        segs = [s.strip() for s in part.split(";")]
        if len(segs) >= 2:
            url = segs[0].lstrip("<").rstrip(">")
            rel = segs[1].split("=")[-1].strip('"')
            links[rel] = url
    return links


# --- Replace your existing helpers with these versions ---


def _wait_for_rate_limit_reset(resp: requests.Response):
    """
    Pause until GitHub says we can resume.
    - Primary limit: uses X-RateLimit-Reset.
    - Secondary/abuse: uses Retry-After (seconds).
    """
    # Handle Retry-After (secondary/abuse) first if present
    retry_after = resp.headers.get("Retry-After")
    if retry_after:
        try:
            secs = int(retry_after)
        except ValueError:
            secs = 60  # fallback
        _print_once(f"[RateLimit] Secondary limit (Retry-After={secs}s). Waiting…")
        _countdown(secs, label="Secondary limit")
        return

    # Primary rate limit
    remaining = int(resp.headers.get("X-RateLimit-Remaining", "1") or "1")
    if remaining > 0:
        return  # nothing to do

    reset_ts = int(resp.headers.get("X-RateLimit-Reset", "0") or "0")
    now = int(time.time())
    wait = max(0, reset_ts - now) + 2  # +2s safety
    reset_at = (
        time.strftime("%H:%M:%S", time.localtime(reset_ts)) if reset_ts else "unknown"
    )
    _print_once(
        f"[RateLimit] Primary limit hit. Resets at {reset_at}. Waiting {wait}s…"
    )
    _countdown(wait, label="Primary limit", end_ts=reset_ts if reset_ts else None)


def _paged_get(url: str, headers: Dict[str, str], params: Dict[str, Any] | None = None):
    """
    Yield responses across pages, auto-pausing on rate limits
    (both primary and secondary).
    """
    while True:
        resp = requests.get(url, headers=headers, params=params)
        # 403 can be either primary or secondary limits
        if resp.status_code == 403 and (
            "rate limit" in resp.text.lower() or "abuse detection" in resp.text.lower()
        ):
            _wait_for_rate_limit_reset(resp)
            # Retry same page/URL after we waited
            continue

        # Some enterprise setups send 429 for secondary limits
        if resp.status_code == 429:
            _wait_for_rate_limit_reset(resp)
            continue

        resp.raise_for_status()
        yield resp

        # Check remaining allowance and pause if necessary before next page
        _wait_for_rate_limit_reset(resp)

        links = _parse_link_header(resp.headers.get("Link", ""))
        if "next" not in links:
            break
        url, params = links["next"], None  # follow absolute next link


def _iso_date(d: Optional[datetime]) -> Optional[str]:
    return None if d is None else d.date().isoformat()


def _needs_glob(pat: str) -> bool:
    return any(ch in pat for ch in "*?[]")


# ---------- Global SEARCH: files (code)


def search_files_globally(
    heuristic: Heuristic, token: Optional[str]
) -> List[Dict[str, Any]]:
    results: Dict[str, Dict[str, Any]] = {}
    for pat in heuristic.files:
        if _needs_glob(pat):
            q = f"path:{pat}"
        else:
            q = f'filename:"{pat}"'

        params = {"q": q, "per_page": 100}
        headers = _auth_headers(token, accept="application/vnd.github.text-match+json")

        for resp in _paged_get(f"{GITHUB_API}/search/code", headers, params):
            payload = resp.json()
            for item in payload.get("items", []):
                path = item.get("path") or ""
                if any(_match_pattern(p, path) for p in heuristic.files):
                    key = f"{item['repository']['full_name']}::{path}"
                    results[key] = {
                        "repo": item["repository"]["full_name"],
                        "path": path,
                        "html_url": item.get("html_url"),
                        "score": item.get("score"),
                    }
    return list(results.values())


# ---------- Global SEARCH: commits


def _commit_queries_from_heuristic(h: Heuristic) -> List[str]:
    queries: Set[str] = set()
    for p in h.commit_message_prefix:
        if p.strip():
            queries.add(f'"{p.strip()}"')
    for name in h.author_names:
        if name.strip():
            queries.add(f'"{name.strip()}"')
    for mail in h.author_mails:
        if mail.strip():
            queries.add(f'"{mail.strip()}"')
    if not queries:
        queries.add("fix")
    return sorted(queries)


def search_commits_globally(
    heuristic: Heuristic, token: Optional[str]
) -> List[Dict[str, Any]]:
    since = _iso_date(heuristic.period_start)
    until = _iso_date(heuristic.period_end) if heuristic.period_end else None

    headers = _auth_headers(token, accept="application/vnd.github.cloak-preview+json")
    matches: Dict[str, Dict[str, Any]] = {}

    for qbase in _commit_queries_from_heuristic(heuristic):
        q = qbase
        if since or until:
            if since and until:
                q = f"{q} author-date:{since}..{until}"
            elif since:
                q = f"{q} author-date:>={since}"
            else:
                q = f"{q} author-date:<={until}"
        params = {"q": q, "per_page": 100, "sort": "committer-date", "order": "desc"}

        for resp in _paged_get(f"{GITHUB_API}/search/commits", headers, params):
            payload = resp.json()
            for item in payload.get("items", []):
                commit = item.get("commit", {})
                msg = commit.get("message") or ""
                author = commit.get("author") or {}
                author_login = (item.get("author") or {}).get("login") or ""
                author_identity = " ".join(
                    [
                        author_login,
                        author.get("name") or "",
                        author.get("email") or "",
                    ]
                ).strip()

                if heuristic.match_commit(msg, author_identity):
                    key = item.get("sha")
                    if key:
                        matches[key] = {
                            "repo": item["repository"]["full_name"],
                            "sha": item.get("sha"),
                            "html_url": item.get("html_url"),
                            "author_login": author_login or None,
                            "author_name": author.get("name") or None,
                            "author_email": author.get("email") or None,
                            "date": author.get("date"),
                            "message": msg,
                        }

    return list(matches.values())


# ---------- Global Scan


def global_scan(
    heuristic: Heuristic,
    incl_files: bool = True,
    incl_commits: bool = True,
    token: Optional[str] = None,
) -> Dict[str, Any]:
    files = []
    commits = []
    repos_from_files = set()
    repos_from_commits = set()

    if incl_files:
        print("files...")
        files = search_files_globally(heuristic, token)
        repos_from_files = {f["repo"] for f in files}
    if incl_commits:
        print("commits...")
        commits = search_commits_globally(heuristic, token)
        repos_from_commits = {c["repo"] for c in commits}
    seed_repos = sorted(repos_from_files | repos_from_commits)
    return {
        "seed_repo_count": len(seed_repos),
        "files": files,
        "commits": commits,
    }


def count_matching(
    heuristic: Heuristic, *, token: Optional[str] = None
) -> Dict[str, Any]:
    global_scan(heuristic, token=token)
    return {k: (len(v) if isinstance(v, list) else v) for k, v in result.items()}


# ---------- Example usage

if __name__ == "__main__":
    from datetime import datetime

    set_rate_limit_logging(True)
    h = Heuristic(
        author_names=("jane.doe",),
        author_mails=("jane@example.com",),
        files=("app.rb", "**/footer.rb"),
        branch_name_prefix=("feature/", "re:release-\\d+"),
        commit_message_prefix=("fix", "refactor"),
        period_start=datetime(2024, 1, 1),
        period_end=None,
    )

    token = os.getenv("GITHUB_TOKEN")
    if token:
        print("Found GitHub PAT token!")
    else:
        print("No GitHub PAT token found!")
    result = global_scan(h, token=token)
    from pprint import pprint

    pprint({k: (len(v) if isinstance(v, list) else v) for k, v in result.items()})
