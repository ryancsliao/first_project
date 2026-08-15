"""Client for pokemontcg.io - used to resolve cards and TCGPlayer market prices."""

from __future__ import annotations

from typing import Optional

import requests

from pokedeal.models import Card

BASE_URL = "https://api.pokemontcg.io/v2"

# Preference order when a watchlist entry doesn't pin down a specific
# print/variant. Earlier entries win.
DEFAULT_VARIANT_PRIORITY = [
    "holofoil",
    "reverseHolofoil",
    "normal",
    "1stEditionHolofoil",
    "1stEditionNormal",
    "unlimitedHolofoil",
    "unlimited",
]


class CardNotFoundError(RuntimeError):
    pass


class PokemonTcgClient:
    def __init__(self, api_key: Optional[str] = None, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()
        self.api_key = api_key

    def _headers(self) -> dict:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["X-Api-Key"] = self.api_key
        return headers

    def find_card(
        self, name: str, set_name: Optional[str] = None, number: Optional[str] = None
    ) -> Card:
        """Look up a card. Raises CardNotFoundError if nothing matches."""
        clauses = [f'name:"{name}"']
        if set_name:
            clauses.append(f'set.name:"{set_name}"')
        if number:
            clauses.append(f"number:{number}")
        query = " ".join(clauses)

        resp = self.session.get(
            f"{BASE_URL}/cards",
            params={"q": query, "pageSize": 10},
            headers=self._headers(),
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])
        if not data:
            raise CardNotFoundError(
                f"No pokemontcg.io match for name={name!r} set={set_name!r} number={number!r}"
            )
        return _card_from_json(data[0])


def _card_from_json(card_json: dict) -> Card:
    tcgplayer = card_json.get("tcgplayer") or {}
    prices = tcgplayer.get("prices") or {}
    return Card(
        id=card_json.get("id", ""),
        name=card_json.get("name", ""),
        set_name=(card_json.get("set") or {}).get("name", ""),
        number=str(card_json.get("number", "")),
        prices=prices,
        raw=card_json,
    )


def pick_market_price(
    card: Card, preferred_variant: Optional[str] = None
) -> tuple[Optional[str], Optional[float]]:
    """Choose which print/variant's market price to use.

    Returns (variant_name, market_price) or (None, None) if no usable price
    is available at all.
    """
    if not card.prices:
        return None, None

    if preferred_variant:
        variant_prices = card.prices.get(preferred_variant)
        if variant_prices and variant_prices.get("market") is not None:
            return preferred_variant, float(variant_prices["market"])
        # Explicit variant requested but not priced - don't silently fall
        # back to a different print, that would be comparing apples to oranges.
        return None, None

    for variant in DEFAULT_VARIANT_PRIORITY:
        variant_prices = card.prices.get(variant)
        if variant_prices and variant_prices.get("market") is not None:
            return variant, float(variant_prices["market"])

    # Nothing in the priority list matched - fall back to whatever variant
    # is present with a market price.
    for variant, variant_prices in card.prices.items():
        if variant_prices and variant_prices.get("market") is not None:
            return variant, float(variant_prices["market"])

    return None, None
