"""The synthetic data must behave like real shoppers, for the default seed and for other seeds."""
from collections import Counter
from statistics import median

import pytest

from peshkash.catalog import CAT_KEYS
from peshkash.datagen import generate, load_sqlite, write_csv, write_sqlite
from peshkash.features import SEG_KEYS, customer_view
from peshkash.realism import realism_report


def test_every_realism_check_passes(raw_customers):
    failing = [f"{c.label}: {c.shown} (expected {c.expected})" for c in realism_report(raw_customers) if not c.ok]
    assert not failing, failing


@pytest.mark.parametrize("seed", [7, 2024])
def test_realism_holds_for_other_seeds(seed):
    failing = [c.key for c in realism_report(generate(1500, seed)) if not c.ok]
    assert not failing


def test_same_seed_same_data_and_different_seed_different_data():
    assert generate(50, 1) == generate(50, 1)
    assert generate(50, 1) != generate(50, 2)


def test_ids_are_unique(raw_customers):
    assert len({c["id"] for c in raw_customers}) == len(raw_customers)


def test_every_segment_appears_and_none_dominates(customers):
    counts = Counter(c["seg"] for c in customers)
    assert set(counts) == set(SEG_KEYS)
    assert max(counts.values()) / len(customers) < .4


def test_engine_view_hides_the_persona(raw_customers, customers):
    assert all("_persona" in c for c in raw_customers)
    assert not any(k.startswith("_") for c in customers for k in c)


def test_orders_are_inside_history_and_after_signup(raw_customers):
    for c in raw_customers:
        for o in c["orders"]:
            assert 0 <= o["d"] <= min(c["signup_ago"], 550)
        assert [o["d"] for o in c["orders"]] == sorted(o["d"] for o in c["orders"])


def test_repeat_buyers_have_plausible_gaps(customers):
    gaps = [c["usual_gap"] for c in customers if c["total"] >= 4]
    assert 15 <= median(gaps) <= 90


def test_points_and_carts_are_consistent(customers):
    for c in customers:
        assert 0 <= c["pts_exp"] <= c["points"]
        if c["cart"]:
            assert c["cart"]["value"] == sum(x["price"] for x in c["cart"]["items"])
            assert 1 <= c["cart"]["hours_ago"] <= 120


def test_deal_lovers_use_more_coupons(raw_customers, customers):
    persona = {c["id"]: c["_persona"] for c in raw_customers}
    deal = [c["disc_aff"] for c in customers if persona[c["id"]] == "deal_seeker" and c["total"] >= 3]
    loyal = [c["disc_aff"] for c in customers if persona[c["id"]] == "loyal_premium" and c["total"] >= 3]
    assert median(deal) > median(loyal) + .4


def test_drifting_customers_show_high_churn_risk(raw_customers, customers):
    persona = {c["id"]: c["_persona"] for c in raw_customers}
    drifting = [c["churn"] for c in customers if persona[c["id"]] == "at_risk" and c["total"] >= 3]
    regular = [c["churn"] for c in customers if persona[c["id"]] in ("regular", "loyal_premium") and c["total"] >= 3]
    assert median(drifting) > .6 > median(regular)


def test_sqlite_and_csv_round_trip(tmp_path):
    raw = generate(120, 11)
    write_sqlite(raw, tmp_path / "p.db")
    write_csv(raw, tmp_path)
    back = load_sqlite(tmp_path / "p.db")
    assert not any("_persona" in c for c in back)               # hidden unless asked for
    with_p = load_sqlite(tmp_path / "p.db", with_personas=True)
    for a, b in zip(raw, with_p):
        assert {**a, "cart": None} == {**b, "cart": None}
        assert (a["cart"] is None) == (b["cart"] is None)
        if a["cart"]:
            assert sorted(x["name"] for x in a["cart"]["items"]) == sorted(x["name"] for x in b["cart"]["items"])
            assert a["cart"]["value"] == b["cart"]["value"]
    assert (tmp_path / "orders.csv").read_text(encoding="utf-8").startswith("customer_id,days_ago,category")
    assert {c["seg"] for c in map(customer_view, back)} <= set(SEG_KEYS)
    assert all(o["cat"] in CAT_KEYS for c in back for o in c["orders"])
