from pokedeal.models import Card
from pokedeal.tcgprices import pick_market_price


def make_card(prices: dict) -> Card:
    return Card(id="x", name="Test", set_name="Test Set", number="1", prices=prices)


def test_pick_preferred_variant():
    card = make_card(
        {
            "normal": {"market": 5.0},
            "holofoil": {"market": 50.0},
        }
    )
    variant, price = pick_market_price(card, preferred_variant="holofoil")
    assert variant == "holofoil"
    assert price == 50.0


def test_preferred_variant_missing_returns_none_instead_of_guessing():
    card = make_card({"normal": {"market": 5.0}})
    variant, price = pick_market_price(card, preferred_variant="holofoil")
    assert variant is None
    assert price is None


def test_default_priority_order_prefers_holofoil_over_normal():
    card = make_card(
        {
            "normal": {"market": 5.0},
            "holofoil": {"market": 50.0},
        }
    )
    variant, price = pick_market_price(card)
    assert variant == "holofoil"
    assert price == 50.0


def test_falls_back_to_any_priced_variant():
    card = make_card({"1stEditionNormal": {"market": 100.0}})
    variant, price = pick_market_price(card)
    assert variant == "1stEditionNormal"
    assert price == 100.0


def test_no_prices_returns_none():
    card = make_card({})
    variant, price = pick_market_price(card)
    assert variant is None
    assert price is None


def test_variant_present_but_market_missing_is_skipped():
    card = make_card(
        {
            "holofoil": {"market": None, "low": 1.0},
            "normal": {"market": 5.0},
        }
    )
    variant, price = pick_market_price(card)
    assert variant == "normal"
    assert price == 5.0
