"""
config.py — the tunable watchlist for the Uncrewed Systems Regulatory & Procurement Tracker.

This is the one file most worth editing over time. It defines:

  * Which dockets, bills, and court cases are "known" priorities (always surfaced).
  * The keyword sets that decide what counts as "in our lane" across air, ground,
    maritime, and defense.
  * Which agencies and NAICS codes to sweep.
  * How far back each source looks and how aggressively to filter noise.

Everything here is plain data. No network calls, no secrets. Edit, commit, and the
next refresh picks it up.
"""

# ---------------------------------------------------------------------------
# Lookback windows (days). How far back each source reaches on every refresh.
# Bigger = more coverage but more API calls and more noise.
# ---------------------------------------------------------------------------
LOOKBACK_DAYS = {
    "federal_register": 120,
    "regulations_gov": 120,
    "fcc_ecfs": 180,
    "congress": 120,
    "sam_gov": 60,
    "courtlistener": 365,
    "usaspending": 120,
}

# Items scoring below this are dropped as noise, UNLESS they hit the watchlist.
DROP_THRESHOLD = 18

# ---------------------------------------------------------------------------
# Known priority proceedings. These are ALWAYS surfaced (forced relevance) and
# get a "watchlist" badge. Pulled from the vault: Current State, the agent specs,
# and the Regulatory Status Audit.
#
# Each entry has two needle lists, both matched on word boundaries:
#   * ids    -> exact identifiers / unique names. Counted on their own.
#   * topics -> broader terms (e.g. "section 301"). Counted ONLY when the item is
#               already topically relevant (a STRONG term fired), so an unrelated
#               rule citing "Section 301" of some other statute is not mislabeled.
# ---------------------------------------------------------------------------
WATCHLIST_DOCKETS = [
    {
        "key": "section-2209",
        "label": "Section 2209 (Critical Infrastructure UAS Restrictions)",
        "agency": "FAA",
        "category": "regulatory",
        "domain": ["air"],
        "deadline": "2026-07-06",
        "ids": ["faa-2026-4558", "section 2209", "unmanned aircraft flight restriction"],
        "topics": ["uafr"],
    },
    {
        "key": "bvlos-part-108",
        "label": "BVLOS / Part 108 NPRM",
        "agency": "FAA",
        "category": "regulatory",
        "domain": ["air"],
        "deadline": None,
        "ids": ["faa-2025-1908", "bvlos", "beyond visual line of sight"],
        "topics": ["part 108"],
    },
    {
        "key": "gn-26-74",
        "label": "GN 26-74 (Unleashing American Drone Dominance)",
        "agency": "FCC",
        "category": "regulatory",
        "domain": ["air", "spectrum", "supply-chain"],
        "deadline": None,
        "ids": ["gn docket no. 26-74", "gn docket 26-74", "gn 26-74", "drone dominance", "unleashing american drone"],
        "topics": ["26-74"],
        "fcc_proceeding": "26-74",
    },
    {
        "key": "et-26-22",
        "label": "ET 26-22 / DA-26-592 (DJI Security Assessment — comment by Aug 28, 2026)",
        "agency": "FCC",
        "category": "regulatory",
        "domain": ["supply-chain", "air"],
        "deadline": "2026-08-28",
        "ids": ["et docket no. 26-22", "et docket 26-22", "et 26-22", "da-26-592", "dji security assessment"],
        "topics": ["26-22", "covered list"],
        "fcc_proceeding": "26-22",
    },
    {
        "key": "commerce-icts-232",
        "label": "Commerce ICTS / Section 232 (UAS supply chain)",
        "agency": "Commerce/BIS",
        "category": "regulatory",
        "domain": ["supply-chain", "air"],
        "deadline": None,
        "ids": ["bis-2025-0059"],
        "topics": ["icts", "section 232", "information and communications technology"],
    },
    {
        "key": "ustr-301",
        "label": "USTR Section 301 (Drone Investigation)",
        "agency": "USTR",
        "category": "regulatory",
        "domain": ["supply-chain", "air"],
        "deadline": None,
        "ids": ["ustr-2025", "ustr-2026"],
        "topics": ["section 301"],
    },
]

# Named legislative vehicles. Congress.gov has no public full-text search, so we
# match these by name against recent bill titles and actions, and you can pin
# exact bill numbers here as they become known (congress/type/number).
WATCHLIST_BILLS = [
    # GUARD Act of 2026 = H.R. 9129 (119th): "Guarding the U.S. against Adversarial
    # Robotics Dominance Act" (sponsor: Moolenaar). NOT a UAS bill despite the name --
    # it places certain humanoid/quadruped robotics communications equipment on the
    # FCC Covered List (same mechanism as ET 26-22, the DJI Covered List proceeding).
    # Pinned by number and tagged ground + supply-chain. "guard act" stays a gated
    # topic because 9+ unrelated bills reuse the short title.
    {"key": "guard-act", "label": "GUARD Act of 2026 (H.R. 9129, robotics on FCC Covered List)", "congress": 119, "type": "hr", "number": 9129, "ids": ["h.r. 9129", "hr 9129", "adversarial robotics dominance", "guarding the u.s. against adversarial robotics"], "topics": ["guard act"], "domain": ["ground", "supply-chain"]},
    {"key": "build-america-250", "label": "BUILD America 250 Act (Sec. 6009 LiDAR)", "congress": 119, "type": "hr", "number": 8870, "ids": ["build america 250", "h.r. 8870"], "topics": ["lidar"], "domain": ["ground", "supply-chain"]},
    {"key": "safer-skies", "label": "Safer Skies Act (C-UAS)", "congress": 119, "type": "s", "number": 3481, "ids": ["safer skies act", "s. 3481"], "topics": [], "domain": ["defense", "air"]},
    # NDAA is cited by many unrelated rules, so topical-only: tagged only when a
    # strong uncrewed-systems term is also present. Pin a specific bill to force it.
    {"key": "ndaa", "label": "NDAA (UAS provisions)", "ids": [], "topics": ["national defense authorization act", "ndaa"], "domain": ["defense"]},
    {"key": "connected-vehicle", "label": "S. 4429 Connected Vehicle Security Act", "congress": 119, "type": "s", "number": 4429, "ids": ["connected vehicle security act", "s. 4429", "s.4429"], "topics": [], "domain": ["ground", "supply-chain"]},
    {"key": "obbba-90005", "label": "OBBBA Sec. 90005 (C-UAS grants)", "ids": [], "topics": ["90005", "section 90005", "one big beautiful bill"], "domain": ["defense"]},
    # Pin more exact bills like: {"key": "...", "congress": 119, "type": "hr", "number": 1234, ...}
]

# Litigation tracked via CourtListener. court codes: ca9 = 9th Cir., cadc = D.C. Cir.
# `query` drives the CourtListener search; ids/topics drive watchlist tagging of
# other items (kept narrow so a generic DJI mention is not tagged as the case).
WATCHLIST_LITIGATION = [
    {"key": "dji-ca9", "label": "DJI petition (9th Circuit, 26-1029)", "court": "ca9", "query": "DJI", "ids": ["26-1029"], "topics": [], "domain": ["supply-chain", "air"]},
    {"key": "dji-cadc-1260h", "label": "DJI 1260H appeal (D.C. Circuit)", "court": "cadc", "query": "DJI 1260H", "ids": ["1260h"], "topics": [], "domain": ["supply-chain", "air"]},
]

# ---------------------------------------------------------------------------
# Relevance vocabulary. STRONG terms are sufficient on their own to keep an item
# and tag a domain. CONTEXT terms only add weight when a STRONG term is also
# present (so a generic "supply chain" notice does not flood the board).
# Each entry: term -> (weight, [domains])
# ---------------------------------------------------------------------------
STRONG_TERMS = {
    # Air / aviation
    "unmanned aircraft": (16, ["air"]),
    "unmanned aircraft system": (16, ["air"]),
    "uas": (12, ["air"]),
    "uav": (12, ["air"]),
    "drone": (14, ["air"]),
    "suas": (14, ["air"]),
    "small unmanned": (14, ["air"]),
    "beyond visual line of sight": (16, ["air"]),
    "bvlos": (16, ["air"]),
    "advanced air mobility": (16, ["air"]),
    "urban air mobility": (15, ["air"]),
    "powered-lift": (13, ["air"]),
    "powered lift": (13, ["air"]),
    "evtol": (15, ["air"]),
    "vertiport": (13, ["air"]),
    "remote identification": (13, ["air"]),
    "remote id": (12, ["air"]),
    "part 107": (12, ["air"]),
    "part 108": (15, ["air"]),
    "section 2209": (18, ["air"]),
    "detect and avoid": (12, ["air"]),
    "electronic conspicuity": (13, ["air"]),
    # Ground
    "automated driving system": (15, ["ground"]),
    "autonomous vehicle": (14, ["ground"]),
    "automated vehicle": (14, ["ground"]),
    "self-driving": (13, ["ground"]),
    "connected vehicle": (13, ["ground"]),
    "unmanned ground vehicle": (15, ["ground"]),
    "autonomous mobile robot": (13, ["ground"]),
    "delivery robot": (13, ["ground"]),
    "ground robot": (12, ["ground"]),
    # Maritime
    "unmanned surface vessel": (16, ["maritime"]),
    "unmanned surface vehicle": (16, ["maritime"]),
    "uncrewed surface vessel": (16, ["maritime"]),
    "unmanned underwater": (16, ["maritime"]),
    "autonomous underwater": (15, ["maritime"]),
    "autonomous vessel": (15, ["maritime"]),
    "uncrewed maritime": (16, ["maritime"]),
    "maritime autonomous surface ship": (15, ["maritime"]),
    "usv": (11, ["maritime"]),
    "uuv": (12, ["maritime"]),
    # Defense / counter-UAS / procurement
    "counter-uas": (16, ["defense"]),
    "counter uas": (16, ["defense"]),
    "c-uas": (16, ["defense"]),
    "counter-unmanned": (16, ["defense"]),
    "counter unmanned": (16, ["defense"]),
    "blue uas": (16, ["defense"]),
    "green uas": (15, ["defense"]),
    "loitering munition": (14, ["defense"]),
    "group 3 uas": (13, ["defense"]),
    "group 4 uas": (13, ["defense"]),
    "group 5 uas": (13, ["defense"]),
    "replicator": (12, ["defense"]),
    "autonomous systems": (10, ["defense"]),
    # Supply chain / spectrum
    "covered list": (15, ["supply-chain"]),
    "dji": (14, ["supply-chain"]),
    "autel": (14, ["supply-chain"]),
}

CONTEXT_TERMS = {
    "supply chain": (6, ["supply-chain"]),
    "foreign adversary": (6, ["supply-chain"]),
    "section 232": (7, ["supply-chain"]),
    "section 301": (7, ["supply-chain"]),
    "icts": (7, ["supply-chain"]),
    "information and communications technology": (6, ["supply-chain"]),
    "equipment authorization": (6, ["spectrum"]),
    "spectrum": (5, ["spectrum"]),
    "900 mhz": (6, ["spectrum"]),
    "lidar": (6, ["ground"]),
    "type certification": (5, ["air"]),
    "national airspace": (5, ["air"]),
    "airspace": (4, ["air"]),
    "autonomy": (5, ["defense"]),
    "first responder": (4, ["air"]),
    "public safety": (4, ["air"]),
}

# Boost when an item comes from an agency we care about (helps disambiguate
# generic terms like "drone" appearing in an unrelated agency notice).
PRIORITY_AGENCIES = {
    "faa", "federal aviation administration",
    "fcc", "federal communications commission",
    "commerce", "bis", "bureau of industry and security",
    "dhs", "homeland security",
    "dod", "defense", "army", "navy", "air force", "darpa", "diu", "socom",
    "ustr", "trade representative",
    "doj", "justice",
    "ntia", "dot", "transportation",
}

# Federal Register: agency slugs to also sweep directly (in addition to terms).
FR_AGENCY_SLUGS = [
    "federal-aviation-administration",
    "federal-communications-commission",
    "industry-and-security-bureau",
    "homeland-security-department",
    "national-highway-traffic-safety-administration",
    "coast-guard",
    "trade-representative-office-of-united-states",
]

# Federal Register full-text search terms (one query each, merged + deduped).
FR_SEARCH_TERMS = [
    "unmanned aircraft", "drone", "beyond visual line of sight", "advanced air mobility",
    "counter-UAS", "unmanned surface vessel", "automated driving system", "connected vehicle",
]

# Regulations.gov full-text search terms.
REGS_SEARCH_TERMS = [
    "unmanned aircraft", "drone", "BVLOS", "advanced air mobility", "counter-UAS",
    "unmanned surface vessel", "automated driving system",
]

# SAM.gov sweep. Notice types (ptype): o=Solicitation, p=Presolicitation,
# r=Sources Sought, s=Special Notice, k=Combined Synopsis/Solicitation,
# i=Intent to Bundle, g=Sale of Surplus. We want o,p,r,s,k.
SAM_PTYPES = "o,p,r,s,k"
SAM_KEYWORDS = [
    "unmanned aircraft", "unmanned aerial", "drone", "counter-UAS", "counter-unmanned",
    "small UAS", "BVLOS", "advanced air mobility", "unmanned surface vessel",
    "unmanned underwater", "autonomous vehicle", "loitering munition", "Blue UAS",
]
# NAICS codes to sweep (aircraft, search/detection instruments, R&D, shipbuilding, robotics).
SAM_NAICS = [
    "336411",  # Aircraft manufacturing
    "336412",  # Aircraft engine and engine parts
    "336413",  # Other aircraft parts
    "334511",  # Search, detection, navigation, guidance instruments
    "541715",  # R&D in physical, engineering, life sciences
    "541330",  # Engineering services
    "336611",  # Ship building and repairing
    "336612",  # Boat building
    "333120",  # Construction machinery (some UGV)
]

# USAspending keyword sweep for recent awards (context, not solicitations).
USASPENDING_KEYWORDS = [
    "unmanned aircraft", "drone", "counter-UAS", "unmanned surface vessel",
    "advanced air mobility", "Blue UAS",
]

# Human-friendly labels for the four headline domains plus cross-cutting tags.
DOMAIN_LABELS = {
    "air": "Air",
    "ground": "Ground",
    "maritime": "Maritime",
    "defense": "Defense",
    "supply-chain": "Supply Chain",
    "spectrum": "Spectrum",
}

CATEGORY_LABELS = {
    "regulatory": "Regulatory",
    "procurement": "Procurement",
    "legislative": "Legislative",
    "litigation": "Litigation",
}
