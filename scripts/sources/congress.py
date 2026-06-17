"""
Congress.gov API v3 (data.gov key works here).

Important honest limitation: the Congress.gov API has no public full-text search.
So we pull the most recently updated bills and keep those whose TITLE or latest
action text matches our vocabulary or a named watchlist vehicle. Bills with no
UAS keyword in the title can be missed. To guarantee a vehicle is tracked, pin its
exact bill in config.WATCHLIST_BILLS as {key, congress, type, number, ...}.

Docs: https://api.congress.gov/
"""

from __future__ import annotations

import common
import config

LIST_URL = "https://api.congress.gov/v3/bill"

_CHAMBER = {
    "hr": ("house-bill", "H.R."),
    "s": ("senate-bill", "S."),
    "hjres": ("house-joint-resolution", "H.J.Res."),
    "sjres": ("senate-joint-resolution", "S.J.Res."),
    "hconres": ("house-concurrent-resolution", "H.Con.Res."),
    "sconres": ("senate-concurrent-resolution", "S.Con.Res."),
    "hres": ("house-resolution", "H.Res."),
    "sres": ("senate-resolution", "S.Res."),
}


def _bill_url(congress, btype, number) -> str:
    slug, _ = _CHAMBER.get((btype or "").lower(), ("bill", ""))
    return f"https://www.congress.gov/bill/{congress}th-congress/{slug}/{number}"


def _bill_label(btype, number) -> str:
    _, pretty = _CHAMBER.get((btype or "").lower(), ("", (btype or "").upper()))
    return f"{pretty} {number}".strip()


def fetch(keys: dict) -> common.SourceResult:
    res = common.SourceResult("Congress.gov")
    api_key = keys.get("data_gov")
    if not api_key:
        res.status = "skipped"
        res.detail = "no data.gov key (set DATA_GOV_API_KEY)"
        return res

    errors: list[str] = []
    seen: set[str] = set()
    from_dt = common.iso(common.lookback_date("congress")) + "T00:00:00Z"

    # Sweep recent bills across a few pages.
    for offset in (0, 250, 500):
        params = {
            "api_key": api_key,
            "format": "json",
            "limit": 250,
            "offset": offset,
            "sort": "updateDate+desc",
            "fromDateTime": from_dt,
        }
        data, err = common.http_get(LIST_URL, params=params)
        if err:
            errors.append(f"offset {offset}: {err}")
            break
        bills = (data or {}).get("bills", []) or []
        if not bills:
            break
        for b in bills:
            congress = b.get("congress")
            btype = b.get("type")
            number = b.get("number")
            key = f"{congress}-{btype}-{number}"
            if key in seen:
                continue
            seen.add(key)
            title = b.get("title", "") or ""
            action = ((b.get("latestAction") or {}).get("text")) or ""
            item = common.make_item(
                source="Congress.gov",
                native_id=key,
                category="legislative",
                item_type="Bill",
                title=f"{_bill_label(btype, number)}: {title}",
                url=_bill_url(congress, btype, number),
                agency="Congress",
                identifier=_bill_label(btype, number),
                date=(b.get("latestAction") or {}).get("actionDate") or b.get("updateDate"),
                summary=action,
                extra={"latest_action": action},
            )
            if common.keep(item):
                res.items.append(item)

    # Pinned bills (exact numbers) always fetched directly.
    for entry in config.WATCHLIST_BILLS:
        if not all(k in entry for k in ("congress", "type", "number")):
            continue
        url = f"{LIST_URL}/{entry['congress']}/{entry['type']}/{entry['number']}"
        data, err = common.http_get(url, params={"api_key": api_key, "format": "json"})
        if err:
            errors.append(f"pinned {entry['key']}: {err}")
            continue
        b = (data or {}).get("bill") or {}
        if not b:
            continue
        title = b.get("title", "") or entry["label"]
        item = common.make_item(
            source="Congress.gov",
            native_id=f"{entry['congress']}-{entry['type']}-{entry['number']}",
            category="legislative",
            item_type="Bill",
            title=f"{_bill_label(entry['type'], entry['number'])}: {title}",
            url=_bill_url(entry["congress"], entry["type"], entry["number"]),
            agency="Congress",
            identifier=_bill_label(entry["type"], entry["number"]),
            date=(b.get("latestAction") or {}).get("actionDate") or b.get("updateDate"),
            summary=((b.get("latestAction") or {}).get("text")) or "",
        )
        item["watchlist"] = {"key": entry["key"], "label": entry["label"]}
        item["score"] = max(item["score"], 80)
        # A pinned bill's domain is curator-declared and authoritative; apply it
        # (the title may not contain vocabulary terms, e.g. a robotics bill).
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
