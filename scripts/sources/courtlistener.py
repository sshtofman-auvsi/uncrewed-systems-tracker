"""
CourtListener API v4 (free token, header 'Authorization: Token <key>').

Tracks the litigation on the watchlist, primarily the DJI matters in the 9th
Circuit and D.C. Circuit. Best-effort: court coverage in RECAP varies, so this is
a supplement, not a system of record.

Docs: https://www.courtlistener.com/help/api/rest/
"""

from __future__ import annotations

import common
import config

SEARCH = "https://www.courtlistener.com/api/rest/v4/search/"


def fetch(keys: dict) -> common.SourceResult:
    res = common.SourceResult("CourtListener")
    token = keys.get("courtlistener")
    if not token:
        res.status = "skipped"
        res.detail = "no CourtListener token (set COURTLISTENER_TOKEN)"
        return res

    headers = {"Authorization": f"Token {token}"}
    errors: list[str] = []
    seen: set[str] = set()

    for entry in config.WATCHLIST_LITIGATION:
        params = {
            "q": entry["query"],
            "type": "r",            # RECAP dockets/documents
            "order_by": "dateFiled desc",
        }
        if entry.get("court"):
            params["court"] = entry["court"]
        data, err = common.http_get(SEARCH, params=params, headers=headers)
        if err:
            errors.append(f"{entry['key']}: {err}")
            continue
        for row in (data or {}).get("results", [])[:15] or []:
            nid = str(row.get("docket_id") or row.get("id") or row.get("docketNumber") or "")
            if not nid or nid in seen:
                continue
            seen.add(nid)
            case = row.get("caseName") or row.get("caseNameShort") or entry["label"]
            abs_url = row.get("absolute_url") or row.get("docket_absolute_url") or ""
            url = f"https://www.courtlistener.com{abs_url}" if abs_url.startswith("/") else (abs_url or "https://www.courtlistener.com")
            item = common.make_item(
                source="CourtListener",
                native_id=nid,
                category="litigation",
                item_type="Court Docket",
                title=case,
                url=url,
                agency=(row.get("court") or entry.get("court", "")).upper(),
                identifier=row.get("docketNumber", "") or "",
                date=row.get("dateFiled") or row.get("dateArgued"),
                summary=(row.get("suitNature") or "") or case,
            )
            item["watchlist"] = {"key": entry["key"], "label": entry["label"]}
            item["score"] = max(item["score"], 70)
            for d in entry.get("domain", []):
                if d not in item["domains"]:
                    item["domains"].append(d)
            res.items.append(item)

    res.detail = f"{len(res.items)} kept"
    if errors and not res.items:
        res.status = "error"
        res.detail = "; ".join(errors[:3])
    elif errors:
        res.detail += f"; {len(errors)} query error(s)"
    return res
