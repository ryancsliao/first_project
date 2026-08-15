from pokedeal.filters import is_clean_listing, is_graded, is_lot_or_bundle, is_not_the_real_card


def test_clean_raw_card_passes():
    assert is_clean_listing("Charizard 4/102 Base Set Holo Unlimited Pokemon Card") is True


def test_graded_card_is_excluded():
    assert is_graded("Charizard Base Set PSA 9 Holo") is True
    assert is_clean_listing("Charizard Base Set PSA 9 Holo") is False


def test_graded_card_with_perfect_grade():
    assert is_graded("Umbreon VMAX Alt Art BGS 10 Black Label") is True


def test_lot_is_excluded():
    assert is_lot_or_bundle("Pokemon Card Lot of 50 Bulk Common/Uncommon") is True
    assert is_clean_listing("Pokemon Card Lot of 50 Bulk Common/Uncommon") is False


def test_bundle_and_binder_are_excluded():
    assert is_lot_or_bundle("Pokemon Card Bundle - 10 Random Holos") is True
    assert is_lot_or_bundle("Complete 1999 Base Set Binder All 102 Cards") is True


def test_proxy_and_custom_are_excluded():
    assert is_not_the_real_card("Charizard Custom Card Proxy Holo") is True
    assert is_clean_listing("Charizard Custom Card Proxy Holo") is False


def test_digital_code_is_excluded():
    assert is_not_the_real_card("Pokemon TCG Live Online Code Card Charizard") is True


def test_normal_number_does_not_trigger_grade_regex():
    # "4/102" or "#4" shouldn't be mistaken for a grade
    assert is_graded("Charizard 4/102 Base Set") is False
