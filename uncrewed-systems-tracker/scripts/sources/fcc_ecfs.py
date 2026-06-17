"""
FCC Electronic Comment Filing System (ECFS) API (data.gov key).

Pulls filings (comments, reply comments, ex partes, notices) for the FCC
proceedings on the watchlist, e.g. GN 26-74 (Drone Dominance) and ET 26-22
(DJI Covered List reconsideration). This is the "FCC docket comments in our lane"
coverage.

Docs: https://www.fcc.gov/ecfs/help/public-api
"""

from __future__ import annotations

import common
import config

BASE = "https://publicapi.fcc.gov/ecfs/filings"


def _proceedings() -> list[dict]:
    out = []
    for entry in config.WATCHLIST_DOCKETS:
        if entry.get("fcc_proceeding"):
            out.append(entry)
    return out


def fetch(keys: dict) -> common.SourceResult:
    res = common.SourceResult("FCC ECFS")
    api_key = keys.get("data_gov")
    if not api_key:
        res.status = "skipped"
        res.detail = "no data.gov key (set DATA_GOV_API_KEY)"
        return res

    errors: list[str] = []
    diag: list[str] = []
    for entry in _proceedings():
        proc = entry["fcc_proceeding"]
        params = {
            "api_key": api_key,
            "proceedings.name": proc,
            "sort": "date_disseminated,DESC",
            "limit": 50,
        }
        data, err = common.http_get(BASE, params=params)
        if err:
            errors.append(f"{proc}: {err}")
            continue
        filings = _extract_filings(data)
        if not filings and isinstance(data, dict):
            # Surface the real envelope keys so one run reveals the structure.
            diag.append(f"{proc} keys=[{','.join(list(data.keys())[:6])}]")
        for f in filings:
            if not isinstance(f, dict):
                continue
            sub_id = f.get("id_submission") or f.get("id") or ""
            filers = ", ".join(
                (x.get("name") or "").strip()
                for x in (f.get("filers") or []) if x.get("name")
            ) or "(filer not listed)"
            subtype = (f.get("submissiontype") or {})
            type_label = subtype.get("description") or subtype.get("abbreviation") or "Filing"
            date = f.get("date_disseminated") or f.get("date_received") or f.get("date_submission")
            docs = f.get("documents") or []
            doc_url = ""
            if docs and isinstance(docs, list) and isinstance(docs[0], dict):
                doc_url = docs[0].get("src") or ""
            url = doc_url or f"https://www.fcc.gov/ecfs/search/search-filings/filing/{sub_id}"
            title = f"{filers}: {type_label} (FCC {proc})"
            item = common.make_item(
                source="FCC ECFS",
                native_id=sub_id or title,
                category="regulatory",
                item_type=_normalize_type(type_label),
                title=title,
                url=url,
                agency="FCC",
                identifier=f"FCC {proc}",
                date=date,
                summary=(f.get("text_data") or "")[:400],
                extra={"proceeding": proc},
            )
            # Always associate with the watchlist proceeding.
            item["watchlist"] = {"key": entry["key"], "label": entry["label"]}
            item["score"] = max(item["score"], 80)
            for d in entry.get("domain", []):
                if d not in item["domains"]:
                    item["domains"].append(d)
            res.items.append(item)

    res.detail = f"{len(res.items)} kept"
    if not res.items and diag:
        res.detail += " | diag: " + "; ".join(diag)
    if errors and not res.items:
        res.status = "error"
        res.detail = "; ".join(errors[:3])
    elif errors:
        res.detail += f"; {len(errors)} query error(s)"
    return res


def _extract_filings(data):
    """ECFS responses have used different envelope keys; accept the variants."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for k in ("filings", "filing", "results", "data"):
            v = data.get(k)
            if isinstance(v, list):
                return v
    return []


def _normalize_type(label: str) -> str:
    low = (label or "").lower()
    if "reply" in low:
        return "Reply Comment"
    if "comment" in low:
        return "Comment"
    if "ex parte" in low:
        return "Ex Parte"
    if "notice" in low:
        return "Notice"
    return label or "Filing"
