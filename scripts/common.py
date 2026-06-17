"""
common.py — shared helpers for every data source.

Keeps three jobs in one place:
  1. Resilient HTTP (timeouts, retries, never throws to the caller).
  2. Date math (lookback windows, multiple wire formats).
  3. The normalized item schema plus relevance scoring / domain tagging.

Design rule: a single bad source must never crash the build. Every fetch returns
a list (possibly empty); errors are reported through SourceResult, not exceptions.
"""

from __future__ import annotations

import datetime as dt
import functools
import re
import time
from dataclasses import dataclass, field
from typing import Any

import requests

import config

# Hybrid UA: browser-like prefix (some public WAFs, e.g. the Federal Register CDN,
# throttle non-browser agents from cloud IP ranges) while still identifying the tool.
USER_AGENT = "Mozilla/5.0 (compatible; AUVSI-RegTracker/1.0; +https://github.com/sshtofman-auvsi)"


# ---------------------------------------------------------------------------
# Source result wrapper
# ---------------------------------------------------------------------------
@dataclass
class SourceResult:
    name: str
    items: list[dict] = field(default_factory=list)
    status: str = "ok"          # ok | error | skipped
    detail: str = ""            # human-readable note (error text, "no key", counts)

    def as_meta(self) -> dict:
        return {"name": self.name, "status": self.status, "detail": self.detail, "count": len(self.items)}


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------
def http_get(url: str, params: dict | None = None, headers: dict | None = None,
             retries: int = 3, timeout: int = 30) -> tuple[Any, str | None]:
    """GET JSON with exponential backoff. Returns (data, error_string_or_None)."""
    return _http("GET", url, params=params, headers=headers, retries=retries, timeout=timeout)


def http_post(url: str, json_body: dict | None = None, headers: dict | None = None,
              retries: int = 3, timeout: int = 45) -> tuple[Any, str | None]:
    """POST JSON with backoff. Returns (data, error_string_or_None)."""
    return _http("POST", url, json_body=json_body, headers=headers, retries=retries, timeout=timeout)


def _http(method: str, url: str, params=None, json_body=None, headers=None,
          retries: int = 3, timeout: int = 30) -> tuple[Any, str | None]:
    hdrs = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if headers:
        hdrs.update(headers)
    last_err = "unknown error"
    for attempt in range(retries):
        try:
            resp = requests.request(method, url, params=params, json=json_body,
                                    headers=hdrs, timeout=timeout)
            if resp.status_code in (403, 429):
                # 429 is explicit rate limiting; 403 is how some public WAFs
                # (e.g. the Federal Register CDN) shed bursts. Both are worth a
                # backoff-and-retry rather than an immediate give-up.
                wait = min(30, 2 ** attempt * 3)
                last_err = f"HTTP {resp.status_code} (throttled), waited {wait}s"
                time.sleep(wait)
                continue
            if 500 <= resp.status_code < 600:
                last_err = f"HTTP {resp.status_code}"
                time.sleep(2 ** attempt)
                continue
            if resp.status_code >= 400:
                return None, f"HTTP {resp.status_code}: {resp.text[:200]}"
            try:
                return resp.json(), None
            except ValueError:
                return None, "response was not valid JSON"
        except requests.RequestException as exc:
            last_err = f"{type(exc).__name__}: {exc}"
            time.sleep(2 ** attempt)
    return None, last_err


# ---------------------------------------------------------------------------
# Dates
# ---------------------------------------------------------------------------
def today() -> dt.date:
    return dt.date.today()


def lookback_date(source: str) -> dt.date:
    days = config.LOOKBACK_DAYS.get(source, 90)
    return today() - dt.timedelta(days=days)


def iso(d: dt.date) -> str:
    return d.isoformat()


def us_date(d: dt.date) -> str:
    """SAM.gov wants MM/dd/yyyy."""
    return d.strftime("%m/%d/%Y")


def parse_date(value: Any) -> str | None:
    """Best-effort parse of assorted wire formats into an ISO date string."""
    if not value:
        return None
    s = str(value).strip()
    # Trim timestamps / timezones down to the date portion where possible.
    candidates = [
        "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d",
        "%b %d, %Y", "%B %d, %Y",
    ]
    cleaned = s.replace("Z", "+0000")
    for fmt in candidates:
        try:
            return dt.datetime.strptime(cleaned, fmt).date().isoformat()
        except ValueError:
            continue
    # Last resort: pull the first YYYY-MM-DD we can find.
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return m.group(0)
    return None


def days_until(iso_date: str | None) -> int | None:
    d = parse_date(iso_date)
    if not d:
        return None
    try:
        return (dt.date.fromisoformat(d) - today()).days
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Text + scoring
# ---------------------------------------------------------------------------
def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower())


@functools.lru_cache(maxsize=8192)
def _needle_re(needle: str) -> re.Pattern:
    # Word-boundary match so "uas" does not hit "coastal" and "26-74" does not
    # hit the Federal Register document number "2026-74110".
    return re.compile(r"(?<!\w)" + re.escape(needle) + r"(?!\w)")


def _has(blob: str, needle: str) -> bool:
    return bool(needle) and _needle_re(needle).search(blob) is not None


def classify(title: str, summary: str = "", identifier: str = "",
             agency: str = "") -> dict:
    """
    Score relevance and tag domains for a candidate item.

    Returns a dict: {score, domains, matched_terms, watchlist}.
      * STRONG terms count on their own.
      * CONTEXT terms only count if at least one STRONG term matched.
      * Watchlist: an `ids` needle (exact docket/bill number, unique name) counts
        on its own; a `topics` needle only counts when the item is already
        topically relevant (a STRONG term fired). This stops a rule that merely
        cites "Section 301" of an unrelated statute from being tagged as the USTR
        drone case.
      * All matching is word-boundary based.
    """
    blob = _norm(" ".join([title or "", summary or "", identifier or ""]))
    agency_blob = _norm(agency)

    score = 0
    domains: set[str] = set()
    matched: list[str] = []

    strong_hit = False
    for term, (weight, doms) in config.STRONG_TERMS.items():
        if _has(blob, term):
            strong_hit = True
            score += weight
            domains.update(doms)
            matched.append(term)

    if strong_hit:
        for term, (weight, doms) in config.CONTEXT_TERMS.items():
            if _has(blob, term):
                score += weight
                domains.update(doms)
                matched.append(term)

    # Agency boost only when there is already a topical signal.
    if strong_hit and any(a in agency_blob for a in config.PRIORITY_AGENCIES):
        score += 6

    # Watchlist detection (dockets + bills + litigation).
    watchlist = None
    for entry in (config.WATCHLIST_DOCKETS + config.WATCHLIST_BILLS + config.WATCHLIST_LITIGATION):
        hit = None
        for needle in entry.get("ids", []):
            if _has(blob, needle):
                hit = needle
                break
        if not hit and strong_hit:
            for needle in entry.get("topics", []):
                if _has(blob, needle):
                    hit = needle
                    break
        if hit:
            watchlist = {"key": entry["key"], "label": entry["label"]}
            score = max(score, 80)
            domains.update(entry.get("domain", []))
            if hit not in matched:
                matched.append(hit)
            break

    return {
        "score": min(score, 100),
        "domains": sorted(domains),
        "matched_terms": matched[:12],
        "watchlist": watchlist,
    }


def make_item(source: str, native_id: str, category: str, item_type: str,
              title: str, url: str, *, agency: str = "", identifier: str = "",
              date: str | None = None, deadline: str | None = None,
              summary: str = "", extra: dict | None = None) -> dict:
    """Build a normalized item, run classification, and attach it."""
    title = (title or "").strip() or "(untitled)"
    summary = (summary or "").strip()
    cls = classify(title, summary, identifier, agency)
    return {
        "id": f"{source}:{native_id}",
        "source": source,
        "category": category,
        "type": item_type,
        "title": title,
        "url": url or "",
        "agency": (agency or "").strip(),
        "identifier": (identifier or "").strip(),
        "date": parse_date(date),
        "deadline": parse_date(deadline),
        "summary": summary[:600],
        "score": cls["score"],
        "domains": cls["domains"],
        "matched_terms": cls["matched_terms"],
        "watchlist": cls["watchlist"],
        "extra": extra or {},
    }


def keep(item: dict) -> bool:
    """Drop low-signal items, but never drop a watchlist hit."""
    if item.get("watchlist"):
        return True
    return item.get("score", 0) >= config.DROP_THRESHOLD
