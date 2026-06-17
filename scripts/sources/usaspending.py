"""
USAspending API v2 (no key required).

Surfaces recent federal contract AWARDS matching our vocabulary. This is "where
the money actually went" context next to the open solicitations from SAM.gov. Not
a solicitation feed; it complements one.

Docs: https://api.usaspending.gov/
"""

from __future__ import annotations

import common
import config

URL = "https://api.usaspending.gov/api/v2/search/spending_by_award/"

_FIELDS = [
    "Award ID", "Recipient Name", "Awarding Agency", "Awarding Sub Agency",
    "Award Amount", "Description", "Start Date", "Contract Award Type",
]


def fetch(keys: dict) -> common.SourceResult:
    res = common.SourceResult("USAspending")
    start = common.iso(common.lookback_date("usaspending"))
    end = common.iso(common.today())

    body = {
        "filters": {
            "keywords": config.USASPENDING_KEYWORDS,
            "time_period": [{"start_date": start, "end_date": end}],
            "award_type_codes": ["A", "B", "C", "D"],
        },
        "fields": _FIELDS,
        "page": 1,
        "limit": 60,
        "sort": "Award Amount",
        "order": "desc",
    }
    data, err = common.http_post(URL, json_body=body)
    if err:
        res.status = "error"
        res.detail = err
        return res

    for row in (data or {}).get("results", []) or []:
        internal = row.get("generated_internal_id") or row.get("internal_id") or ""
        award_id = row.get("Award ID") or internal or ""
        recipient = row.get("Recipient Name") or "(recipient n/a)"
        agency = row.get("Awarding Agency") or ""
        desc = row.get("Description") or ""
        amount = row.get("Award Amount")
        url = f"https://www.usaspending.gov/award/{internal}" if internal else "https://www.usaspending.gov"
        title = f"{recipient}: {desc[:120]}" if desc else f"Award to {recipient}"
        item = common.make_item(
            source="USAspending",
            native_id=str(award_id) or title,
            category="procurement",
            item_type="Award",
            title=title,
            url=url,
            agency=agency,
            identifier=str(award_id),
            date=row.get("Start Date"),
            summary=desc,
            extra={"amount": amount, "award_type": row.get("Contract Award Type")},
        )
        # Keyword filter already applied server-side; ensure it surfaces.
        item["score"] = max(item["score"], 30)
        res.items.append(item)

    res.detail = f"{len(res.items)} kept"
    return res
