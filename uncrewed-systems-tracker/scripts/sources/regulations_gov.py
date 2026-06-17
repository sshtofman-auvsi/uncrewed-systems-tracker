"""
Regulations.gov API v4 (requires a data.gov API key, header X-Api-Key).

Two passes:
  1. Keyword search for recent documents in our lane (NPRMs, rules, notices).
  2. Direct pull of the watchlist dockets (e.g., FAA-2026-4558) plus their most
     recent public comments and a comment count, so we can show "X comments,
     latest from <party>".

Docs: https://open.gsa.gov/api/regulationsgov/
Rate limit: 1,000 requests/hour on a registered key. We stay well under.
"""

from __future__ import annotations

import common
import config

DOCS = "https://api.regulations.gov/v4/documents"
DOCKETS = "https://api.regulations.gov/v4/dockets"
COMMENTS = "https://api.regulations.gov/v4/comments"

_TYPE_MAP = {
    "Proposed Rule": "NPRM",
    "Rule": "Final Rule",
    "Notice": "Notice",
    "Public Submission": "Comment",
    "Supporting & Related Material": "Supporting Material",
    "Other": "Document",
}


def _watchlist_docket_ids() -> list[dict]:
    """Watchlist entries whose match contains a regulations.gov-style docket id."""
    out = []
    for entry in config.WATCHLIST_DOCKETS:
        for needle in entry.get("ids", []):
            # docket ids look like AGENCY-YEAR-NUMBER
            if needle.count("-") >= 2 and any(c.isdigit() for c in needle):
                out.append({"id": needle.upper(), "entry": entry})
                break
    return out


def fetch(keys: dict) -> common.SourceResult:
    res = common.SourceResult("Regulations.gov")
    api_key = keys.get("data_gov")
    if not api_key:
        res.status = "skipped"
        res.detail = "no data.gov key (set DATA_GOV_API_KEY)"
        return res

    headers = {"X-Api-Key": api_key}
    since = common.iso(common.lookback_date("regulations_gov"))
    seen: set[str] = set()
    errors: list[str] = []

    # Pass 1: keyword search for recent documents.
    for term in config.REGS_SEARCH_TERMS:
        params = {
            "filter[searchTerm]": term,
            "filter[postedDate][ge]": since,
            "sort": "-postedDate",
            "page[size]": 50,
        }
        data, err = common.http_get(DOCS, params=params, headers=headers)
        if err:
            errors.append(f"search '{term}': {err}")
            continue
        for doc in (data or {}).get("data", []) or []:
            _add_document(res, seen, doc)

    # Pass 2: watchlist dockets + recent comments.
    for wl in _watchlist_docket_ids():
        docket_id = wl["id"]
        entry = wl["entry"]
        meta, err = common.http_get(f"{DOCKETS}/{docket_id}", headers=headers)
        title = entry["label"]
        if not err and meta:
            attrs = (meta.get("data") or {}).get("attributes") or {}
            title = attrs.get("title") or title
        # recent comments on this docket
        cparams = {
            "filter[docketId]": docket_id,
            "sort": "-postedDate",
            "page[size]": 5,
        }
        cdata, cerr = common.http_get(COMMENTS, params=cparams, headers=headers)
        if cerr:
            errors.append(f"comments {docket_id}: {cerr}")
        comments = (cdata or {}).get("data", []) or []
        total = ((cdata or {}).get("meta") or {}).get("totalElements")
        for c in comments:
            cattrs = c.get("attributes") or {}
            item = common.make_item(
                source="Regulations.gov",
                native_id=c.get("id", ""),
                category="regulatory",
                item_type="Comment",
                title=f"Comment on {title}: {cattrs.get('title') or '(comment)'}",
                url=f"https://www.regulations.gov/comment/{c.get('id','')}",
                agency=cattrs.get("agencyId", "") or entry.get("agency", ""),
                identifier=docket_id,
                date=cattrs.get("postedDate"),
                summary=cattrs.get("title", "") or "",
                extra={"docket_total_comments": total},
            )
            # force watchlist association
            item["watchlist"] = {"key": entry["key"], "label": entry["label"]}
            item["score"] = max(item["score"], 80)
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


def _add_document(res: common.SourceResult, seen: set, doc: dict) -> None:
    doc_id = doc.get("id")
    if not doc_id or doc_id in seen:
        return
    seen.add(doc_id)
    attrs = doc.get("attributes") or {}
    item_type = _TYPE_MAP.get(attrs.get("documentType", ""), "Document")
    docket_id = attrs.get("docketId") or doc_id
    item = common.make_item(
        source="Regulations.gov",
        native_id=doc_id,
        category="regulatory",
        item_type=item_type,
        title=attrs.get("title", ""),
        url=f"https://www.regulations.gov/document/{doc_id}",
        agency=attrs.get("agencyId", ""),
        identifier=docket_id,
        date=attrs.get("postedDate"),
        deadline=attrs.get("commentEndDate"),
        summary=attrs.get("title", "") or "",
    )
    if common.keep(item):
        res.items.append(item)
