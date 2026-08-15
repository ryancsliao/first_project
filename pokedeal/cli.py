"""Command-line entry point."""

from __future__ import annotations

import argparse
import csv
import logging
import sys

from rich.console import Console
from rich.table import Table

from pokedeal.config import MissingCredentialsError, load_config
from pokedeal.dealfinder import find_deals
from pokedeal.ebay import EbayClient
from pokedeal.models import Deal
from pokedeal.tcgprices import CardNotFoundError, PokemonTcgClient, pick_market_price
from pokedeal.watchlist import WatchlistError, load_watchlist

console = Console()


def _print_deals_table(deals: list[Deal]) -> None:
    if not deals:
        console.print("[yellow]No deals found.[/yellow]")
        return

    table = Table(title=f"Found {len(deals)} deal(s)")
    table.add_column("Card")
    table.add_column("Variant")
    table.add_column("Listing", overflow="fold")
    table.add_column("Price+Ship", justify="right")
    table.add_column("Market", justify="right")
    table.add_column("Discount", justify="right")
    table.add_column("Link", overflow="fold")

    for deal in deals:
        shipping_note = "" if deal.listing.shipping_known else " (ship est.)"
        table.add_row(
            f"{deal.card.name} ({deal.card.set_name} #{deal.card.number})",
            deal.variant,
            deal.listing.title,
            f"${deal.listing.total_price:.2f}{shipping_note}",
            f"${deal.market_price:.2f}",
            f"{deal.discount_pct:.1f}%",
            deal.listing.url,
        )

    console.print(table)


def _write_deals_csv(deals: list[Deal], path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "card_name",
                "set",
                "number",
                "variant",
                "listing_title",
                "listing_price",
                "shipping_cost",
                "shipping_known",
                "total_price",
                "market_price",
                "discount_pct",
                "url",
                "seller",
            ]
        )
        for deal in deals:
            writer.writerow(
                [
                    deal.card.name,
                    deal.card.set_name,
                    deal.card.number,
                    deal.variant,
                    deal.listing.title,
                    f"{deal.listing.price:.2f}",
                    f"{deal.listing.shipping_cost:.2f}",
                    deal.listing.shipping_known,
                    f"{deal.listing.total_price:.2f}",
                    f"{deal.market_price:.2f}",
                    f"{deal.discount_pct:.1f}",
                    deal.listing.url,
                    deal.listing.seller or "",
                ]
            )


def cmd_scan(args: argparse.Namespace) -> int:
    try:
        config = load_config(require_ebay=True)
    except MissingCredentialsError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1

    try:
        entries = load_watchlist(args.watchlist)
    except (WatchlistError, OSError) as exc:
        console.print(f"[red]{exc}[/red]")
        return 1

    min_discount = args.min_discount if args.min_discount is not None else config.default_min_discount_pct

    tcg_client = PokemonTcgClient(api_key=config.pokemontcg_api_key)
    ebay_client = EbayClient(
        client_id=config.ebay_client_id,
        client_secret=config.ebay_client_secret,
        sandbox=config.ebay_is_sandbox,
        marketplace_id=config.ebay_marketplace_id,
    )

    console.print(f"Scanning {len(entries)} watchlist entr{'y' if len(entries)==1 else 'ies'}...")
    deals = find_deals(
        entries,
        tcg_client,
        ebay_client,
        category_id=config.ebay_category_id,
        default_min_discount_pct=min_discount,
    )

    _print_deals_table(deals)

    if args.csv:
        _write_deals_csv(deals, args.csv)
        console.print(f"Wrote {len(deals)} deal(s) to {args.csv}")

    return 0


def cmd_lookup(args: argparse.Namespace) -> int:
    config = load_config(require_ebay=False)
    tcg_client = PokemonTcgClient(api_key=config.pokemontcg_api_key)
    try:
        card = tcg_client.find_card(args.name, args.set, args.number)
    except CardNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1

    variant, market_price = pick_market_price(card, args.variant)

    console.print(f"[bold]{card.name}[/bold] - {card.set_name} #{card.number}")
    if market_price is None:
        console.print("[yellow]No TCGPlayer market price available for this card/variant.[/yellow]")
    else:
        console.print(f"Variant: {variant}    Market price: ${market_price:.2f}")

    if card.prices:
        console.print("All available variants:")
        for v, p in card.prices.items():
            market = p.get("market")
            console.print(f"  {v}: {'$' + format(market, '.2f') if market is not None else 'n/a'}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pokedeal", description="Find Pokemon card eBay listings priced below TCGPlayer market price."
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose logging")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan", help="scan a watchlist for underpriced eBay listings")
    scan.add_argument("--watchlist", default="watchlist.yaml", help="path to watchlist YAML file")
    scan.add_argument(
        "--min-discount",
        type=float,
        default=None,
        help="minimum %% below market price to report (overrides .env default)",
    )
    scan.add_argument("--csv", default=None, help="also write results to this CSV file")
    scan.set_defaults(func=cmd_scan)

    lookup = subparsers.add_parser("lookup", help="look up a card's TCGPlayer market price (no eBay call)")
    lookup.add_argument("name")
    lookup.add_argument("--set", default=None)
    lookup.add_argument("--number", default=None)
    lookup.add_argument("--variant", default=None)
    lookup.set_defaults(func=cmd_lookup)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
