#!/usr/bin/env python3
"""
build.py — fetch every source, assemble the dataset, render the dashboard.

Run modes:
  python build.py            # live fetch using API keys from the environment
  python build.py --demo     # offline render from samples.py (no network/keys)

Outputs (into ../site/):
  data.json    — the full normalized dataset (for programmatic use / Pages)
  index.html   — self-contained dashboard with the data inlined (open from disk)

Environment (live mode), supplied as GitHub Actions secrets:
  DATA_GOV_API_KEY     -> Regulations.gov, FCC ECFS, Congress.gov
  SAM_API_KEY          -> SAM.gov opportunities
  COURTLISTENER_TOKEN  -> CourtListener litigation
Federal Register and USAspending need no key.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import common  # noqa: E402
import config  # noqa: E402
from sources import (  # noqa: E402
    congress, courtlistener, fcc_ecfs, federal_register, regulations_gov,
    sam_gov, usaspending,
)

SITE_DIR = SCRIPT_DIR.parent / "docs"
TEMPLATE = SITE_DIR / "template.html"
DATA_OUT = SITE_DIR / "data.json"
HTML_OUT = SITE_DIR / "index.html"

# Source order controls cross-source dedupe priority (earlier wins).
SOURCES = [
    ("Federal Register", federal_register.fetch),
    ("Regulations.gov", regulations_gov.fetch),
    ("FCC ECFS", fcc_ecfs.fetch),
    ("Congress.gov", congress.fetch),
    ("SAM.gov", sam_gov.fetch),
    ("CourtListener", courtlistener.fetch),
    ("USAspending", usaspending.fetch),
]


def load_keys() -> dict:
    return {
        "data_gov": os.environ.get("DATA_GOV_API_KEY", "").strip(),
        "sam": os.environ.get("SAM_API_KEY", "").strip(),
        "courtlistener": os.environ.get("COURTLISTENER_TOKEN", "").strip(),
    }


def run_live(keys: dict) -> tuple[list[dict], list[dict]]:
    items: list[dict] = []
    meta: list[dict] = []
    for name, fn in SOURCES:
        try:
            result = fn(keys)
        except Exception as exc:  # never let one source kill the build
            result = common.SourceResult(name, status="error", detail=f"unhandled: {exc}")
        items.extend(result.items)
        meta.append(result.as_meta())
        print(f"  {name:18s} {result.status:8s} {result.detail}")
    return items, meta


def run_demo() -> tuple[list[dict], list[dict]]:
    import samples
    items: list[dict] = []
    meta: list[dict] = []
    for result in samples.results():
        items.extend(result.items)
        m = result.as_meta()
        m["status"] = "demo" if result.items else "skipped"
        meta.append(m)
    return items, meta


def _fingerprint(item: dict) -> str:
    title = re.sub(r"\s+", " ", item.get("title", "").lower())[:60]
    return f"{item.get('type','')}|{item.get('identifier','').lower()}|{title}"


def dedupe(items: list[dict]) -> list[dict]:
    seen: dict[str, dict] = {}
    out: list[dict] = []
    for it in items:
        fp = _fingerprint(it)
        if fp in seen:
            # keep the higher-scoring one
            if it.get("score", 0) > seen[fp].get("score", 0):
                idx = out.index(seen[fp])
                out[idx] = it
                seen[fp] = it
            continue
        seen[fp] = it
        out.append(it)
    return out


def load_prior_first_seen() -> dict:
    if not DATA_OUT.exists():
        return {}
    try:
        prior = json.loads(DATA_OUT.read_text(encoding="utf-8"))
        return {it["id"]: it.get("first_seen") for it in prior.get("items", []) if it.get("id")}
    except Exception:
        return {}


def mark_new(items: list[dict], prior: dict, now_iso: str) -> int:
    had_prior = bool(prior)
    new_count = 0
    recent_cut = (common.today() - dt.timedelta(days=10)).isoformat()
    for it in items:
        prev = prior.get(it["id"])
        it["first_seen"] = prev or now_iso
        if had_prior:
            is_new = it["id"] not in prior
        else:
            # First ever build: flag genuinely recent items so the UI is not blank.
            is_new = bool(it.get("date")) and it["date"] >= recent_cut
        it["is_new"] = is_new
        if is_new:
            new_count += 1
    return new_count


def build_watchlist(items: list[dict]) -> list[dict]:
    out = []
    entries = (
        [("regulatory", e) for e in config.WATCHLIST_DOCKETS]
        + [("legislative", e) for e in config.WATCHLIST_BILLS]
        + [("litigation", e) for e in config.WATCHLIST_LITIGATION]
    )
    for category, entry in entries:
        hits = [it for it in items if (it.get("watchlist") or {}).get("key") == entry["key"]]
        latest = max((it.get("date") or "" for it in hits), default="")
        deadline = entry.get("deadline")
        # Only let same-category items set a deadline (so a procurement RFP that
        # merely mentions "BVLOS" cannot override the BVLOS docket comment deadline).
        if not deadline:
            same_cat = [it.get("deadline") for it in hits if it.get("category") == category and it.get("deadline")]
            future = sorted(d for d in same_cat if d >= common.today().isoformat())
            if future:
                deadline = future[0]
        out.append({
            "key": entry["key"],
            "label": entry["label"],
            "category": category,
            "agency": entry.get("agency", ""),
            "domain": entry.get("domain", []),
            "deadline": deadline,
            "count": len(hits),
            "latest": latest,
        })
    # Sort: soonest deadline first, then most hits.
    out.sort(key=lambda w: (w["deadline"] or "9999", -w["count"]))
    return out


def build_deadlines(items: list[dict]) -> list[dict]:
    today_iso = common.today().isoformat()
    rows = []
    for it in items:
        dl = it.get("deadline")
        if dl and dl >= today_iso:
            rows.append({
                "deadline": dl,
                "days": common.days_until(dl),
                "title": it["title"],
                "identifier": it.get("identifier", ""),
                "category": it.get("category"),
                "source": it.get("source"),
                "url": it.get("url"),
            })
    rows.sort(key=lambda r: r["deadline"])
    return rows[:40]


def build_stats(items: list[dict], new_count: int) -> dict:
    def tally(field):
        d: dict[str, int] = {}
        for it in items:
            vals = it.get(field)
            if isinstance(vals, list):
                for v in vals:
                    d[v] = d.get(v, 0) + 1
            elif vals:
                d[vals] = d.get(vals, 0) + 1
        return dict(sorted(d.items(), key=lambda kv: -kv[1]))

    return {
        "total": len(items),
        "new": new_count,
        "by_category": tally("category"),
        "by_domain": tally("domains"),
        "by_source": tally("source"),
    }


def assemble(items: list[dict], meta: list[dict], demo: bool) -> dict:
    now = dt.datetime.now(dt.timezone.utc)
    now_iso = now.isoformat()
    items = dedupe(items)
    new_count = mark_new(items, load_prior_first_seen(), now_iso)
    # Default ordering: relevance, then newest.
    items.sort(key=lambda it: (it.get("score", 0), it.get("date") or ""), reverse=True)
    return {
        "generated_at": now_iso,
        "generated_human": now.strftime("%Y-%m-%d %H:%M UTC"),
        "demo": demo,
        "items": items,
        "sources": meta,
        "stats": build_stats(items, new_count),
        "watchlist": build_watchlist(items),
        "deadlines": build_deadlines(items),
        "domain_labels": config.DOMAIN_LABELS,
        "category_labels": config.CATEGORY_LABELS,
    }


def render(payload: dict) -> None:
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    DATA_OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    template = TEMPLATE.read_text(encoding="utf-8")
    inline = json.dumps(payload, ensure_ascii=False)
    # Keep inlined data from terminating the <script> block or the JS comment.
    inline = inline.replace("</", "<\\/").replace("*/", "*\\/")
    html = template.replace("/*__DATA_PAYLOAD__*/null", inline)
    HTML_OUT.write_text(html, encoding="utf-8")
    print(f"\nWrote {DATA_OUT.relative_to(SITE_DIR.parent)} and {HTML_OUT.relative_to(SITE_DIR.parent)}")
    print(f"Items: {payload['stats']['total']}  New: {payload['stats']['new']}  Demo: {payload['demo']}")


def main() -> int:
    demo = "--demo" in sys.argv
    print(f"Building tracker ({'DEMO' if demo else 'LIVE'})...")
    if demo:
        items, meta = run_demo()
    else:
        keys = load_keys()
        present = [k for k, v in keys.items() if v]
        print(f"  keys present: {present or 'none (no-key sources only)'}")
        items, meta = run_live(keys)
    payload = assemble(items, meta, demo)
    render(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
