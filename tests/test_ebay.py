import json

from pokedeal.ebay import EbayClient


class FakeResponse:
    def __init__(self, status_code=200, json_body=None, text=""):
        self.status_code = status_code
        self._json_body = json_body or {}
        self.text = text or json.dumps(self._json_body)

    def json(self):
        return self._json_body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, token_expires_in=7200):
        self.post_calls = []
        self.get_calls = []
        self.token_expires_in = token_expires_in
        self._token_counter = 0

    def post(self, url, headers=None, data=None, timeout=None):
        self.post_calls.append((url, headers, data))
        self._token_counter += 1
        return FakeResponse(
            json_body={
                "access_token": f"token-{self._token_counter}",
                "expires_in": self.token_expires_in,
            }
        )

    def get(self, url, headers=None, params=None, timeout=None):
        self.get_calls.append((url, headers, params))
        return FakeResponse(json_body={"itemSummaries": [{"itemId": "1", "title": "Charizard"}]})


def test_token_is_reused_across_calls():
    session = FakeSession()
    client = EbayClient("id", "secret", session=session)

    client.search_items("Charizard")
    client.search_items("Charizard")

    assert len(session.post_calls) == 1  # only fetched a token once
    assert len(session.get_calls) == 2
    assert session.get_calls[0][1]["Authorization"] == "Bearer token-1"


def test_token_is_refreshed_once_expired():
    session = FakeSession(token_expires_in=30)  # under the 60s refresh margin
    client = EbayClient("id", "secret", session=session)

    client.search_items("Charizard")
    client.search_items("Charizard")

    assert len(session.post_calls) == 2  # refreshed because it was within the margin


def test_search_items_returns_item_summaries():
    session = FakeSession()
    client = EbayClient("id", "secret", session=session)

    results = client.search_items("Charizard", category_id="183454", limit=10)

    assert results == [{"itemId": "1", "title": "Charizard"}]
    _, _, params = session.get_calls[0]
    assert params["q"] == "Charizard"
    assert params["category_ids"] == "183454"
    assert params["limit"] == "10"


def test_sandbox_uses_sandbox_hosts():
    session = FakeSession()
    client = EbayClient("id", "secret", sandbox=True, session=session)
    client.search_items("Charizard")
    assert "sandbox" in session.post_calls[0][0]
    assert "sandbox" in session.get_calls[0][0]
