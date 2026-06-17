# Uncrewed Systems Regulatory & Procurement Tracker

Live dashboard of federal regulatory and procurement activity relevant to
uncrewed systems across **air, ground, maritime, and defense**. Maintained by
AUVSI Regulatory Affairs.

## View it

**https://sshtofman-auvsi.github.io/uncrewed-systems-tracker/**

> Update this URL if you name the repository something other than
> `uncrewed-systems-tracker`.

Nothing to install. The page shows when it was last updated. Use the filters
(category, domain, source, type, search), the **Upcoming deadlines** panel, and
the **Watchlist status** panel. "New since last refresh" flags items added since
the prior run.

## What it tracks

- Regulatory NPRMs, final rules, and notices (Federal Register, Regulations.gov)
- Public docket comments (Regulations.gov, FCC ECFS)
- Contract opportunities: RFPs, CSOs, Sources Sought, Special Notices, RFS (SAM.gov)
- Federal contract awards (USAspending)
- UAS-related legislation (Congress.gov)
- Tracked litigation, e.g. the DJI matters (CourtListener)

Items are scored for relevance and tagged by domain. A curated watchlist
(Section 2209, BVLOS/Part 108, GN 26-74, ET 26-22, Commerce ICTS/232, USTR 301,
named bills, DJI litigation) is always surfaced.

## How "live" works

A GitHub Actions workflow (`.github/workflows/refresh.yml`) runs every 6 hours
and on demand. It fetches the federal APIs, rebuilds `docs/index.html` and
`docs/data.json`, and commits them back. GitHub Pages serves `docs/`.

To refresh now (collaborators): **Actions -> Refresh Regulatory Tracker -> Run workflow**, then reload the page.

## API keys (one-time, repository secrets)

Settings -> Secrets and variables -> Actions -> New repository secret:

| Secret | Unlocks | Where to get it |
|---|---|---|
| `DATA_GOV_API_KEY` | Regulations.gov, FCC ECFS, Congress.gov | https://api.data.gov/signup/ |
| `SAM_API_KEY` | SAM.gov opportunities (RFP/CSO/Sources Sought/RFS) | SAM.gov account -> Profile -> Public API Key |
| `COURTLISTENER_TOKEN` | DJI litigation dockets | https://www.courtlistener.com/ -> Profile -> API token |

Federal Register and USAspending need no key. A source with no key simply shows
"skipped" in the dashboard's source-health bar and lights up once its secret is
added.

## Tuning what it tracks

Edit `scripts/config.py` — watchlist, relevance vocabulary, keyword/NAICS sweeps,
and lookback windows. Commit, and the next refresh applies it.

## Run it locally

```bash
pip install -r requirements.txt
python scripts/build.py --demo                 # offline preview, no keys
export DATA_GOV_API_KEY=... SAM_API_KEY=... COURTLISTENER_TOKEN=...
python scripts/build.py                         # live build
```

Both write `docs/index.html` and `docs/data.json`.

## Limitation

This is a monitoring aid. Always verify against the official docket,
solicitation, or bill text before acting or filing.
