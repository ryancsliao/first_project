"""Load a YAML watchlist file into WatchlistEntry objects."""

from __future__ import annotations

import yaml

from pokedeal.models import WatchlistEntry


class WatchlistError(RuntimeError):
    pass


def load_watchlist(path: str) -> list[WatchlistEntry]:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if not raw:
        raise WatchlistError(f"{path} is empty")
    if not isinstance(raw, list):
        raise WatchlistError(f"{path} must be a YAML list of card entries")

    entries = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict) or "name" not in item:
            raise WatchlistError(f"Entry #{i + 1} in {path} needs at least a 'name' field")
        entries.append(
            WatchlistEntry(
                name=item["name"],
                set_name=item.get("set"),
                number=str(item["number"]) if item.get("number") is not None else None,
                variant=item.get("variant"),
                min_discount_pct=item.get("min_discount_pct"),
                query=item.get("query"),
                max_results=int(item.get("max_results", 50)),
            )
        )
    return entries
