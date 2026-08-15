"""Heuristic title filters.

eBay listing titles are free text, so matching a listing to a specific
TCGPlayer-priced print is inherently fuzzy. Rather than pretend to solve
that with NLP, we keep the matching simple (the search query does the
heavy lifting) and use these filters to throw out listings that would make
the price comparison meaningless: graded cards (worth far more/less than
a raw market price), lots/bundles (per-card price isn't the listing price),
and proxies/customs/digital codes (not the real card at all).
"""

from __future__ import annotations

import re

GRADED_RE = re.compile(
    r"\b(PSA|BGS|CGC|SGC|ACE|HGA|GMA)\s*-?\s*(10|[1-9](\.5)?)\b", re.IGNORECASE
)

LOT_KEYWORDS = [
    "lot of",
    "bundle",
    "bulk lot",
    "job lot",
    "joblot",
    "complete set",
    "binder",
    "collection lot",
    "mystery box",
    "mystery pack",
]

NOT_THE_REAL_CARD_KEYWORDS = [
    "proxy",
    "custom card",
    "customs",
    "fake",
    "replica",
    "digital",
    "online code",
    "tcg live code",
    "tcgo code",
    "orica",
    "art print",
    "metal card",
]


def is_graded(title: str) -> bool:
    return bool(GRADED_RE.search(title))


def is_lot_or_bundle(title: str) -> bool:
    lowered = title.lower()
    return any(keyword in lowered for keyword in LOT_KEYWORDS)


def is_not_the_real_card(title: str) -> bool:
    lowered = title.lower()
    return any(keyword in lowered for keyword in NOT_THE_REAL_CARD_KEYWORDS)


def is_clean_listing(title: str) -> bool:
    """True if this looks like a single raw/ungraded real card listing."""
    return not (is_graded(title) or is_lot_or_bundle(title) or is_not_the_real_card(title))
