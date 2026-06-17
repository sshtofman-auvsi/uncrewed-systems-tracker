"""
Federal Register API (no key required).

Covers proposed rules (NPRMs), final rules, and notices across every agency.
This is the backbone of the "regulatory NPRM" coverage and works with zero keys,
so it produces live data on the very first refresh.

Docs: https://www.federalregister.gov/developers/documentation/api/v1
"""

from __future__ import annotations

import time

import common
import config

BASE = "https://www.federalregister.gov/api/v1/documents.json"

_TYPE_MAP = {
    "Proposed Rule": ("NPRM", "regulatory"),
    "Rule": ("Final Rule", "regulatory"),
    "Notice": ("Notice", "regulatory"),
    "Presidential Document": ("Presidential Doc", "regulatory"),
}

_FIELDS = [
    "document_number", "title", "type", "abstract", "publication_date",
    "html_url", "agencies", "comments_close_on", "docket_ids", "comment_url",
]


def fetch(keys: dict) -> common.SourceResult:
    res = common.SourceResult("Federal Register")
    since = common.iso(common.lookback_date("federal_register"))
    seen: set[str] = set()
    errors: list[str] = []

    for i, term in enumerate(config.FR_SEARCH_TERMS):
        if i:
            time.sleep(1.0)  # be polite to the public API; avoids burst 403s
        params = {
            "per_page": 100,
            "order": "newest",
            "conditions[term]": term,
            "conditions[publication_date][gte]": since,
            "conditions[type][]": ["RULE", "PRORULE", "NOTICE"],
            "fields[]": _FIELDS,
        }
        data, err = common.http_get(BASE, params=params)
        if err:
            errors.append(f"'{term}': {err}")
            continue
        for doc in (data or {}).get("results", []) or []:
            num = doc.get("document_number")
            if not num or num in seen:
                continue
            seen.add(num)
            item_type, category = _TYPE_MAP.get(doc.get("type", ""), ("Document", "regulatory"))
            agencies = doc.get("agencies") or []
            agency = ", ".join(a.get("name", "") for a in agencies if a.get("name"))[:120]
            dockets = doc.get("docket_ids") or []
            identifier = dockets[0] if dockets else num
            item = common.make_item(
                source="Federal Register",
                native_id=num,
                category=category,
                item_type=item_type,
                title=doc.get("title", ""),
                url=doc.get("html_url", ""),
                agency=agency,
                identifier=identifier,
                date=doc.get("publication_date"),
                deadline=doc.get("comments_close_on"),
                summary=doc.get("abstract", "") or "",
                extra={"comment_url": doc.get("comment_url"), "dockets": dockets},
            )
            if common.keep(item):
                res.items.append(item)

    if errors and not res.items:
        res.status = "error"
        res.detail = "; ".join(errors[:3])
    elif errors:
        res.detail = f"{len(res.items)} kept; {len(errors)} query error(s)"
    else:
        res.detail = f"{len(res.items)} kept"
    return res
