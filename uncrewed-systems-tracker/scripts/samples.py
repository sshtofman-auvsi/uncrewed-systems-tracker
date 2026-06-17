"""
samples.py — offline fixtures for demo mode.

Used only when build.py runs with --demo (or no network). Lets the dashboard
render a representative, openable page before any API keys or GitHub Actions runs
exist. Content is illustrative and clearly flagged as sample data in the UI.
"""

from __future__ import annotations

import common


def _r(name, items):
    res = common.SourceResult(name)
    res.items = items
    res.detail = f"{len(items)} sample"
    return res


def results() -> list[common.SourceResult]:
    fr = [
        common.make_item("Federal Register", "2026-14021", "regulatory", "NPRM",
                         "Operation of Unmanned Aircraft Systems Over Critical Infrastructure (Section 2209)",
                         "https://www.federalregister.gov/", agency="Federal Aviation Administration",
                         identifier="FAA-2026-4558", date="2026-05-06", deadline="2026-07-06",
                         summary="Proposed framework for unmanned aircraft flight restrictions over fixed-site critical infrastructure under Section 2209."),
        common.make_item("Federal Register", "2025-22110", "regulatory", "NPRM",
                         "Beyond Visual Line of Sight Operations of Unmanned Aircraft (Part 108)",
                         "https://www.federalregister.gov/", agency="Federal Aviation Administration",
                         identifier="FAA-2025-1908", date="2026-05-28", deadline="2026-08-15",
                         summary="Reopened comment period on electronic conspicuity provisions of the Part 108 BVLOS NPRM."),
        common.make_item("Federal Register", "2026-09931", "regulatory", "Notice",
                         "Section 232 National Security Investigation of Imported Unmanned Aircraft Systems",
                         "https://www.federalregister.gov/", agency="Bureau of Industry and Security",
                         identifier="BIS-2025-0059", date="2026-06-02",
                         summary="Notice of investigation and request for public comment on UAS supply chain and import dependence."),
    ]
    sam = [
        common.make_item("SAM.gov", "demo-cso-001", "procurement", "CSO",
                         "Commercial Solutions Opening: Counter-UAS Detection and Mitigation",
                         "https://sam.gov/", agency="DEPT OF DEFENSE", identifier="W56KGY-26-S-0007",
                         date="2026-06-09", deadline="2026-07-15",
                         summary="Seeking commercial counter-unmanned aircraft systems for fixed-site defense.",
                         extra={"naics": "334511"}),
        common.make_item("SAM.gov", "demo-ss-002", "procurement", "Sources Sought",
                         "Sources Sought: Unmanned Surface Vessel Autonomy Payloads",
                         "https://sam.gov/", agency="DEPT OF THE NAVY", identifier="N0002426SS1234",
                         date="2026-06-11", deadline="2026-06-30",
                         summary="Market research for autonomous unmanned surface vessel payload integration.",
                         extra={"naics": "336611"}),
        common.make_item("SAM.gov", "demo-rfp-003", "procurement", "Solicitation (RFP)",
                         "Small UAS for Public Safety BVLOS Operations",
                         "https://sam.gov/", agency="DEPT OF HOMELAND SECURITY", identifier="70RDAD26R00000099",
                         date="2026-06-13", deadline="2026-07-28",
                         summary="Procurement of small UAS platforms supporting beyond visual line of sight first responder operations."),
    ]
    congress = [
        common.make_item("Congress.gov", "119-s-4429", "legislative", "Bill",
                         "S. 4429: Connected Vehicle Security Act",
                         "https://www.congress.gov/", agency="Congress", identifier="S. 4429",
                         date="2026-06-04", summary="Referred to Committee on Commerce, Science, and Transportation."),
        common.make_item("Congress.gov", "119-hr-2021", "legislative", "Bill",
                         "H.R. 2021: GUARD Act",
                         "https://www.congress.gov/", agency="Congress", identifier="H.R. 2021",
                         date="2026-05-30", summary="Counter-UAS authority and unmanned aircraft security provisions."),
    ]
    fcc = [
        common.make_item("FCC ECFS", "demo-fcc-1", "regulatory", "Reply Comment",
                         "AUVSI — Reply Comment (FCC 26-74)", "https://www.fcc.gov/ecfs/",
                         agency="FCC", identifier="FCC 26-74", date="2026-05-18",
                         summary="Reply comment in Unleashing American Drone Dominance proceeding."),
        common.make_item("FCC ECFS", "demo-fcc-2", "regulatory", "Comment",
                         "Public Power Association — Comment (FCC 26-74)", "https://www.fcc.gov/ecfs/",
                         agency="FCC", identifier="FCC 26-74", date="2026-05-01",
                         summary="Comment on covered list and supply chain provisions."),
    ]
    court = [
        common.make_item("CourtListener", "demo-court-1", "litigation", "Court Docket",
                         "DJI Technology Inc. v. Department of Defense", "https://www.courtlistener.com/",
                         agency="CADC", identifier="No. 1260H", date="2026-04-22",
                         summary="Appeal of Section 1260H listing decision."),
    ]
    usa = [
        common.make_item("USAspending", "demo-award-1", "procurement", "Award",
                         "Skydio Inc.: Blue UAS production and sustainment", "https://www.usaspending.gov/",
                         agency="Department of Defense", identifier="HQ072726C0012",
                         date="2026-05-20", summary="Contract award for Blue UAS small unmanned aircraft.",
                         extra={"amount": 24500000}),
    ]
    # Force several through the keep() floor regardless of scoring quirks.
    for grp in (sam, usa):
        for it in grp:
            it["score"] = max(it["score"], 35)
    return [_r("Federal Register", fr), _r("Regulations.gov", []), _r("FCC ECFS", fcc),
            _r("Congress.gov", congress), _r("SAM.gov", sam),
            _r("CourtListener", court), _r("USAspending", usa)]
