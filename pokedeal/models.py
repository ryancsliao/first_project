"""Plain data structures shared across the package."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class WatchlistEntry:
    """One card a user wants to watch for deals on."""

    name: str
    set_name: Optional[str] = None
    number: Optional[str] = None
    variant: Optional[str] = None
    min_discount_pct: Optional[float] = None
    query: Optional[str] = None  # override the eBay search query text
    max_results: int = 50

    def search_query(self) -> str:
        if self.query:
            return self.query
        parts = [self.name]
        if self.set_name:
            parts.append(self.set_name)
        return " ".join(parts)


@dataclass
class Card:
    """A card resolved from the pokemontcg.io API."""

    id: str
    name: str
    set_name: str
    number: str
    prices: dict[str, dict[str, Optional[float]]] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class Listing:
    """A single eBay item summary."""

    item_id: str
    title: str
    price: float
    currency: str
    shipping_cost: float
    shipping_known: bool
    condition: Optional[str]
    url: str
    seller: Optional[str] = None

    @property
    def total_price(self) -> float:
        return self.price + self.shipping_cost


@dataclass
class Deal:
    """A listing that beats the market price by at least the target margin."""

    entry: WatchlistEntry
    card: Card
    variant: str
    market_price: float
    listing: Listing
    discount_pct: float
