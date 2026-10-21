import pytest

from split import compute_shares, expand_items, split_amount


def test_split_ten_euros_three_ways():
    assert split_amount(1000, [1, 1, 1]) == [334, 333, 333]


def test_extra_cent_goes_to_payer():
    assert split_amount(1000, [1, 1, 1], prefer=2) == [333, 333, 334]


def test_split_two_to_one():
    assert split_amount(900, [2, 1]) == [600, 300]


def test_expand_two_beers():
    pieces = expand_items([{"name": "Pivo", "quantity": 2, "price": 8.00}])
    assert [p["price_cents"] for p in pieces] == [400, 400]
    assert pieces[0]["group_id"] == pieces[1]["group_id"]


def test_expand_uneven_pieces():
    pieces = expand_items([{"name": "Krof", "quantity": 3, "price": 10.00}])
    assert [p["price_cents"] for p in pieces] == [334, 333, 333]


def test_single_item_stays_one_piece():
    pieces = expand_items([{"name": "Krače", "quantity": 1, "price": 2.38}])
    assert len(pieces) == 1 and pieces[0]["price_cents"] == 238


def test_shares_sum_to_total():
    items = [{"id": "a", "price_cents": 1000}, {"id": "b", "price_cents": 450}]
    assignments = {"a": {"jaz": 1, "ana": 1, "miha": 1}, "b": {"ana": 1}}
    owed = compute_shares(items, ["jaz", "ana", "miha"], assignments, payer="jaz")
    assert owed == {"jaz": 334, "ana": 783, "miha": 333}
    assert sum(owed.values()) == 1450
    assert all(v >= 0 for v in owed.values())


def test_unassigned_item_rejected():
    with pytest.raises(ValueError):
        compute_shares([{"id": "a", "price_cents": 100}], ["jaz"], {}, payer="jaz")
