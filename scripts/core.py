"""Self-contained core for the no-database version.

'Most recent' == 'highest filing ids' (the ids are sequential), so we discover
the current frontier id on demand and walk down to collect the newest filings.
No storage: results are held only in a short-lived in-memory cache to avoid
hammering the source, and the HTTP response is CDN-cached on top of that.
"""
import base64
import concurrent.futures as cf
import html as _html
import re
import threading
import time

import requests

BASE = "https://reports.ethics.ny.gov/publicquery"
UA = "nylobby-latest/1.0 (personal recent-NY-lobbying-filings viewer)"
FRONTIER_GUESS = 822164      # a recent id; forward search handles growth from here
PROBE = 14                   # ids per "is anything here?" probe (gaps make a single id unreliable)
WALK = 36                    # ids per batch when collecting the newest filings
CONCURRENCY = 10
CACHE_TTL = 150              # seconds to reuse a computed result in a warm process

_session_local = threading.local()


def _session():
    s = getattr(_session_local, "s", None)
    if s is None:
        s = _session_local.s = requests.Session()
        s.headers.update({"User-Agent": UA, "Accept": "text/html"})
    return s


def token(n: int) -> str:
    s = base64.b64encode(str(int(n)).encode()).decode()
    pad = s.count("=")
    return s.replace("=", "").replace("+", "-").replace("/", "_") + str(pad)


def view_url(n: int) -> str:
    return f"{BASE}/ViewFiling/{token(n)}"


def _fetch(n: int):
    """Return (id, status, html). status 200 = filing, 'GAP' = none here."""
    url = view_url(n)
    for _ in range(3):
        try:
            r = _session().get(url, timeout=15)
            if r.status_code == 200:
                return n, 200, r.text
            if r.status_code == 500:
                return n, "GAP", ""
        except requests.RequestException:
            time.sleep(0.4)
    return n, "ERR", ""


def _fetch_many(ids):
    out = {}
    with cf.ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
        for n, st, html in ex.map(_fetch, ids):
            out[n] = (st, html)
    return out


_WS = re.compile(r"\s+")
_TAGS = re.compile(r"<[^>]+>")
_H2 = re.compile(r"<h2\b[^>]*>(.*?)</h2>", re.S | re.I)
_PERIOD = re.compile(r"FILING PERIOD:\s*([^<\n]+)", re.I)
# The card is: <h4 ...>LABEL</h4> ... <strong ...>NAME</strong>
_CLIENT = re.compile(r"CONTRACTUAL CLIENT.*?<strong[^>]*>(.*?)</strong>", re.S | re.I)
_LOBBYIST = re.compile(r"PRINCIPAL LOBBYIST.*?<strong[^>]*>(.*?)</strong>", re.S | re.I)


def _clean(s):
    out = _WS.sub(" ", _TAGS.sub(" ", _html.unescape(s or "")).replace("\xa0", " ")).strip()
    return "" if out == "None" else out


def parse(n, html):
    """Minimal record for the list view via regex (fast on 55KB pages), or None
    if the page is empty / not a filing."""
    m = _H2.search(html)
    if not m:
        return None
    filing_type = _clean(m.group(1))
    if not filing_type:
        return None
    cm, lm = _CLIENT.search(html), _LOBBYIST.search(html)
    client = _clean(cm.group(1)) if cm else ""
    lobbyist = _clean(lm.group(1)) if lm else ""
    if not client and not lobbyist:
        return None  # skip blank/incomplete filings
    pm = _PERIOD.search(html)
    return {
        "id": n,
        "filing_type": filing_type,
        "period": _clean(pm.group(1)) if pm else "",
        "client_name": client,
        "lobbyist_name": lobbyist,
        "url": view_url(n),
    }


def find_frontier(start=None):
    """Highest id that currently returns a filing.

    Filing ids only ever grow, so a hardcoded recent guess is always <= the true
    frontier: we exponentially probe upward to bracket it, then binary-search the
    boundary. Each probe scans a small window because gaps make single ids
    unreliable."""
    lo = start or FRONTIER_GUESS

    def has_any(x):
        res = _fetch_many(range(x, x + PROBE))
        return any(st == 200 for st, _ in res.values())

    # In the unlikely case the guess is already past the frontier, step down.
    if not has_any(lo):
        while lo > 0 and not has_any(lo):
            lo -= PROBE * 12
        lo = max(lo, 0)
    # Exponentially bracket the frontier above lo.
    step = PROBE * 8
    hi = lo + step
    while has_any(hi):
        lo, step = hi, step * 2
        hi = lo + step
    # Binary-search the boundary to within one probe window.
    while hi - lo > PROBE:
        mid = (lo + hi) // 2
        if has_any(mid):
            lo = mid
        else:
            hi = mid
    res = _fetch_many(range(lo, hi + PROBE))
    oks = [i for i, (st, _) in res.items() if st == 200]
    return max(oks) if oks else lo


def _compute_latest(n):
    frontier = find_frontier()
    filings = []
    cursor = frontier
    empty_streak = 0
    while len(filings) < n and cursor > 0 and empty_streak < 4:
        ids = list(range(max(1, cursor - WALK + 1), cursor + 1))
        res = _fetch_many(ids)
        found = False
        for i in sorted(ids, reverse=True):
            st, html = res.get(i, ("GAP", ""))
            if st == 200:
                rec = parse(i, html)
                if rec:
                    filings.append(rec)
                    found = True
                    if len(filings) >= n:
                        break
        empty_streak = 0 if found else empty_streak + 1
        cursor -= WALK
    return {"filings": filings, "frontier": frontier, "generated_at": time.time()}


_cache = {"data": None, "at": 0}
_lock = threading.Lock()


def latest(n=40):
    now = time.time()
    with _lock:
        if _cache["data"] and now - _cache["at"] < CACHE_TTL:
            return _cache["data"]
    data = _compute_latest(n)
    with _lock:
        _cache["data"] = data
        _cache["at"] = time.time()
    return data
