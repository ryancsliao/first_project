"""Configuration loading from environment variables / .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    ebay_client_id: str
    ebay_client_secret: str
    ebay_env: str
    ebay_marketplace_id: str
    ebay_category_id: str
    pokemontcg_api_key: str | None
    default_min_discount_pct: float

    @property
    def ebay_is_sandbox(self) -> bool:
        return self.ebay_env.strip().upper() == "SANDBOX"


class MissingCredentialsError(RuntimeError):
    """Raised when required eBay credentials are not configured."""


def load_config(require_ebay: bool = True) -> Config:
    """Load configuration from environment variables (and a local .env file).

    Set require_ebay=False for commands that don't need eBay access (e.g.
    a plain TCGPlayer price lookup).
    """
    load_dotenv()

    client_id = os.getenv("EBAY_CLIENT_ID", "").strip()
    client_secret = os.getenv("EBAY_CLIENT_SECRET", "").strip()

    if require_ebay and (not client_id or not client_secret):
        raise MissingCredentialsError(
            "EBAY_CLIENT_ID / EBAY_CLIENT_SECRET are not set.\n"
            "Copy .env.example to .env and fill in your eBay developer "
            "application credentials (see https://developer.ebay.com/)."
        )

    try:
        min_discount = float(os.getenv("DEFAULT_MIN_DISCOUNT_PCT", "20"))
    except ValueError:
        min_discount = 20.0

    return Config(
        ebay_client_id=client_id,
        ebay_client_secret=client_secret,
        ebay_env=os.getenv("EBAY_ENV", "PRODUCTION"),
        ebay_marketplace_id=os.getenv("EBAY_MARKETPLACE_ID", "EBAY_US"),
        ebay_category_id=os.getenv("EBAY_CATEGORY_ID", "183454"),
        pokemontcg_api_key=os.getenv("POKEMONTCG_API_KEY", "").strip() or None,
        default_min_discount_pct=min_discount,
    )
