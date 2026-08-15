from pokedeal.dealfinder import find_deals_for_entry, listing_from_item_summary
from pokedeal.models import Card, WatchlistEntry
from pokedeal.tcgprices import CardNotFoundError


class FakeTcgClient:
    def __init__(self, card=None, error=None):
        self.card = card
        self.error = error

    def find_card(self, name, set_name=None, number=None):
        if self.error:
            raise self.error
        return self.card


class FakeEbayClient:
    def __init__(self, items):
        self.items = items
        self.calls = []

    def search_items(self, query, category_id=None, limit=50):
        self.calls.append((query, category_id, limit))
        return self.items


def make_item(title, price, currency="USD", shipping=None, item_id="1"):
    item = {
        "itemId": item_id,
        "title": title,
        "price": {"value": str(price), "currency": currency},
        "itemWebUrl": f"https://ebay.com/itm/{item_id}",
    }
    if shipping is not None:
        item["shippingOptions"] = [{"shippingCost": {"value": str(shipping), "currency": currency}}]
    return item


def test_listing_from_item_summary_extracts_shipping():
    item = make_item("Charizard 4/102 Base Set Holo", 40.0, shipping=4.5)
    listing = listing_from_item_summary(item)
    assert listing.price == 40.0
    assert listing.shipping_cost == 4.5
    assert listing.shipping_known is True
    assert listing.total_price == 44.5


def test_listing_without_shipping_info_defaults_to_zero():
    item = make_item("Charizard 4/102 Base Set Holo", 40.0)
    listing = listing_from_item_summary(item)
    assert listing.shipping_cost == 0.0
    assert listing.shipping_known is False


def test_finds_deal_below_threshold():
    card = Card(
        id="x", name="Charizard", set_name="Base Set", number="4",
        prices={"holofoil": {"market": 100.0}},
    )
    entry = WatchlistEntry(name="Charizard", set_name="Base Set", number="4", variant="holofoil")
    tcg = FakeTcgClient(card=card)
    items = [
        make_item("Charizard 4/102 Base Set Holo NM", 60.0, shipping=0.0, item_id="deal"),
        make_item("Charizard 4/102 Base Set Holo PSA 9", 500.0, item_id="graded"),
        make_item("Charizard 4/102 Base Set Holo NM", 95.0, item_id="not-a-deal"),
    ]
    ebay = FakeEbayClient(items)

    deals = find_deals_for_entry(entry, tcg, ebay, category_id="183454", default_min_discount_pct=20)

    assert len(deals) == 1
    assert deals[0].listing.item_id == "deal"
    assert deals[0].discount_pct == 40.0
    assert ebay.calls == [("Charizard Base Set", "183454", 50)]


def test_card_not_found_returns_no_deals():
    entry = WatchlistEntry(name="Not A Real Card")
    tcg = FakeTcgClient(error=CardNotFoundError("nope"))
    ebay = FakeEbayClient([])

    deals = find_deals_for_entry(entry, tcg, ebay, category_id=None, default_min_discount_pct=20)

    assert deals == []


def test_no_market_price_returns_no_deals():
    card = Card(id="x", name="Mystery Card", set_name="Set", number="1", prices={})
    entry = WatchlistEntry(name="Mystery Card")
    tcg = FakeTcgClient(card=card)
    ebay = FakeEbayClient([make_item("Mystery Card", 5.0)])

    deals = find_deals_for_entry(entry, tcg, ebay, category_id=None, default_min_discount_pct=20)

    assert deals == []


def test_per_entry_min_discount_override():
    card = Card(id="x", name="Pikachu", set_name="Base Set", number="58", prices={"normal": {"market": 10.0}})
    entry = WatchlistEntry(name="Pikachu", min_discount_pct=5)
    tcg = FakeTcgClient(card=card)
    ebay = FakeEbayClient([make_item("Pikachu 58/102 Base Set", 9.2, item_id="small-deal")])

    # global default of 20% would reject this, but the entry override of 5% should accept it
    deals = find_deals_for_entry(entry, tcg, ebay, category_id=None, default_min_discount_pct=20)

    assert len(deals) == 1
    assert deals[0].listing.item_id == "small-deal"
