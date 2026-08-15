"""Orchestration: resolve a watchlist entry's market price, search eBay,
filter/score listings, and return the deals worth surfacing."""

from __future__ import annotations

import logging
from typing import Iterable, Optional

from pokedeal.ebay import EbayClient
from pokedeal.filters import is_clean_listing
from pokedeal.models import Card, Deal, Listing, WatchlistEntry
from pokedeal.tcgprices import CardNotFoundError, PokemonTcgClient, pick_market_price

logger = logging.getLogger(__name__)


def listing_from_item_summary(item: dict) -> Optional[Listing]:
    price_info = item.get("price") or {}
    if price_info.get("value") is None:
        return None

    shipping_cost = 0.0
    shipping_known = False
    for option in item.get("shippingOptions") or []:
        cost = (option.get("shippingCost") or {}).get("value")
        if cost is not None:
            shipping_cost = float(cost)
            shipping_known = True
            break  # take the first/cheapest listed option

    return Listing(
        item_id=item.get("itemId", ""),
        title=item.get("title", ""),
        price=float(price_info["value"]),
        currency=price_info.get("currency", "USD"),
        shipping_cost=shipping_cost,
        shipping_known=shipping_known,
        condition=item.get("condition"),
        url=item.get("itemWebUrl", ""),
        seller=(item.get("seller") or {}).get("username"),
    )


def find_deals_for_entry(
    entry: WatchlistEntry,
    tcg_client: PokemonTcgClient,
    ebay_client: EbayClient,
    category_id: Optional[str],
    default_min_discount_pct: float,
) -> list[Deal]:
    try:
        card = tcg_client.find_card(entry.name, entry.set_name, entry.number)
    except CardNotFoundError as exc:
        logger.warning("Skipping %r: %s", entry.name, exc)
        return []

    variant, market_price = pick_market_price(card, entry.variant)
    if market_price is None:
        logger.warning(
            "Skipping %r: no TCGPlayer market price available (variant=%r)",
            entry.name,
            entry.variant,
        )
        return []

    min_discount_pct = entry.min_discount_pct
    if min_discount_pct is None:
        min_discount_pct = default_min_discount_pct

    raw_items = ebay_client.search_items(
        entry.search_query(), category_id=category_id, limit=entry.max_results
    )

    deals: list[Deal] = []
    for item in raw_items:
        title = item.get("title", "")
        if not is_clean_listing(title):
            continue

        listing = listing_from_item_summary(item)
        if listing is None or listing.currency != "USD" or listing.total_price <= 0:
            continue

        discount_pct = (market_price - listing.total_price) / market_price * 100
        if discount_pct >= min_discount_pct:
            deals.append(
                Deal(
                    entry=entry,
                    card=card,
                    variant=variant,
                    market_price=market_price,
                    listing=listing,
                    discount_pct=discount_pct,
                )
            )

    return deals


def find_deals(
    entries: Iterable[WatchlistEntry],
    tcg_client: PokemonTcgClient,
    ebay_client: EbayClient,
    category_id: Optional[str],
    default_min_discount_pct: float,
) -> list[Deal]:
    all_deals: list[Deal] = []
    for entry in entries:
        all_deals.extend(
            find_deals_for_entry(
                entry, tcg_client, ebay_client, category_id, default_min_discount_pct
            )
        )
    all_deals.sort(key=lambda d: d.discount_pct, reverse=True)
    return all_deals
