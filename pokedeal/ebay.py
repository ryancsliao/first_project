"""Client for eBay's Browse API (application/client-credentials access only -
read-only public listing data, no user login required)."""

from __future__ import annotations

import base64
import time
from typing import Optional

import requests

PRODUCTION_HOSTS = {
    "auth": "https://api.ebay.com/identity/v1/oauth2/token",
    "api": "https://api.ebay.com",
}
SANDBOX_HOSTS = {
    "auth": "https://api.sandbox.ebay.com/identity/v1/oauth2/token",
    "api": "https://api.sandbox.ebay.com",
}

OAUTH_SCOPE = "https://api.ebay.com/oauth/api_scope"

# Refresh a bit before actual expiry so we never fire a request with a token
# that dies mid-flight.
TOKEN_REFRESH_MARGIN_SECONDS = 60


class EbayAuthError(RuntimeError):
    pass


class EbayClient:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        sandbox: bool = False,
        marketplace_id: str = "EBAY_US",
        session: Optional[requests.Session] = None,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.hosts = SANDBOX_HOSTS if sandbox else PRODUCTION_HOSTS
        self.marketplace_id = marketplace_id
        self.session = session or requests.Session()

        self._token: Optional[str] = None
        self._token_expires_at: float = 0.0

    def _get_token(self) -> str:
        now = time.time()
        if self._token and now < self._token_expires_at - TOKEN_REFRESH_MARGIN_SECONDS:
            return self._token

        credentials = f"{self.client_id}:{self.client_secret}".encode("utf-8")
        basic_auth = base64.b64encode(credentials).decode("ascii")

        resp = self.session.post(
            self.hosts["auth"],
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {basic_auth}",
            },
            data={"grant_type": "client_credentials", "scope": OAUTH_SCOPE},
            timeout=15,
        )
        if resp.status_code != 200:
            raise EbayAuthError(
                f"eBay OAuth token request failed ({resp.status_code}): {resp.text}"
            )
        payload = resp.json()
        self._token = payload["access_token"]
        self._token_expires_at = now + float(payload.get("expires_in", 7200))
        return self._token

    def search_items(
        self,
        query: str,
        category_id: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """Return raw item_summary dicts from the Browse API search endpoint."""
        token = self._get_token()
        params = {
            "q": query,
            "limit": str(min(max(limit, 1), 200)),
        }
        if category_id:
            params["category_ids"] = category_id

        resp = self.session.get(
            f"{self.hosts['api']}/buy/browse/v1/item_summary/search",
            headers={
                "Authorization": f"Bearer {token}",
                "X-EBAY-C-MARKETPLACE-ID": self.marketplace_id,
                "Accept": "application/json",
            },
            params={**params, "fieldgroups": "EXTENDED"},
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json().get("itemSummaries", []) or []
