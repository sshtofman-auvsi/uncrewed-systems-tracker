"""
SAM.gov Opportunities API v2 (requires a SAM.gov API key).

This is the contract-opportunity source: RFPs, CSOs, Sources Sought, Special
Notices, Combined Synopsis/Solicitations, and Requests for Solutions.

Two sweeps:
  1. Keyword (title) sweep — SAM has already matched our term in the title, so we
     keep every result and just tag domains.
  2. NAICS sweep — broader; kept only if our vocabulary also fires (filters out
     generic aircraft/ship solicitations that are not uncrewed-systems related).

Docs: https://open.gsa.gov/api/get-opportunities-public-api/
Note: SAM enforces per-day quotas on public keys. Keep the keyword/NAICS lists
lean and the refresh cadence reasonable (see .github/workflows/refresh.yml).
"""

from __future__ import annotations

import common
import config

BASE = "https://api.sam.gov/opportunities/v2/search"

_TYPE_MAP = {
    "Solicitation": "Solicitation (RFP)",
    "Presolicitation": "Presolicitation",
    "Sources Sought": "Sources Sought",
    "Special Notice": "Special Notice",
    "Combined Synopsis/Solicitation": "Combined Synopsis",
    "Award Notice": "Award Notice",
}


def _label_type(raw_type: str, title: str) -> str:
    """Refine the notice type using title cues for CSO / RFS."""
    t = (title or "").lower()
    base = _TYPE_MAP.get(raw_type, raw_type or "Notice")
    if "commercial solutions opening" in t or "cso" in t.split():
        return "CSO"
    if "request for solution" in t or "request for solutions" in t:
        return "Request for Solutions"
    if "request for information" in t or t.strip().startswith("rfi"):
        return "RFI"
    return base


def fetch(keys: dict) -> common.SourceResult:
    res = common.SourceResult("SAM.gov")
    api_key = keys.get("sam")
    if not api_key:
        res.status = "skipped"
        res.detail = "no SAM.gov key (set SAM_API_KEY)"
        return res

    posted_from = common.us_date(common.lookback_date("sam_gov"))
    posted_to = common.us_date(common.today())
    seen: set[str] = set()
    errors: list[str] = []

    # Pass 1: keyword sweep (keep everything SAM returns for these terms).
    for kw in config.SAM_KEYWORDS:
        params = {
            "api_key": api_key,
            "postedFrom": posted_from,
            "postedTo": posted_to,
            "ptype": config.SAM_PTYPES,
            "title": kw,
            "limit": 100,
        }
        data, err = common.http_get(BASE, params=params)
        if err:
            errors.append(f"kw '{kw}': {err}")
            continue
        for opp in (data or {}).get("opportunitiesData", []) or []:
            _add_opp(res, seen, opp, force=True)

    # Pass 2: NAICS sweep (keep only when our vocabulary fires).
    for naics in config.SAM_NAICS:
        params = {
            "api_key": api_key,
            "postedFrom": posted_from,
            "postedTo": posted_to,
            "ptype": config.SAM_PTYPES,
            "ncode": naics,
            "limit": 100,
        }
        data, err = common.http_get(BASE, params=params)
        if err:
            errors.append(f"naics {naics}: {err}")
            continue
        for opp in (data or {}).get("opportunitiesData", []) or []:
            _add_opp(res, seen, opp, force=False)

    res.detail = f"{len(res.items)} kept"
    if errors and not res.items:
        res.status = "error"
        res.detail = "; ".join(errors[:3])
    elif errors:
        res.detail += f"; {len(errors)} query error(s)"
    return res


def _add_opp(res: common.SourceResult, seen: set, opp: dict, force: bool) -> None:
    nid = opp.get("noticeId")
    if not nid or nid in seen:
        return
    title = opp.get("title", "") or ""
    raw_type = opp.get("type") or opp.get("baseType") or ""
    agency = opp.get("fullParentPathName", "") or opp.get("organizationType", "")
    sol = opp.get("solicitationNumber") or nid
    item = common.make_item(
        source="SAM.gov",
        native_id=nid,
        category="procurement",
        item_type=_label_type(raw_type, title),
        title=title,
        url=opp.get("uiLink", "") or f"https://sam.gov/opp/{nid}/view",
        agency=agency.split(".")[0] if agency else "",
        identifier=sol,
        date=opp.get("postedDate"),
        deadline=opp.get("responseDeadLine"),
        summary=title,
        extra={"naics": opp.get("naicsCode"), "setaside": opp.get("typeOfSetAside")},
    )
    if force:
        # Title already matched our keyword in SAM's own search.
        item["score"] = max(item["score"], 35)
        seen.add(nid)
        res.items.append(item)
    elif common.keep(item):
        seen.add(nid)
        res.items.append(item)
