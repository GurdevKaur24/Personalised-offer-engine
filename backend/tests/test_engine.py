from collections import Counter

import pytest

from helpers import cart, customer, order
from peshkash.checker import check_offer, failed, is_quiet
from peshkash.engine import decide, in_holdout, next_send_time
from peshkash.rules import Rules

R = Rules()


def campaign(customers, r):
    spent, out = 0, []
    for c in customers:
        d = decide(c, r, spent)
        if d.offer:
            spent += d.offer.cost
        out.append(d)
    return out, spent


def test_every_offer_in_a_campaign_passes_the_checker(customers):
    decisions, spent = campaign(customers, R)
    sent = [d for d in decisions if d.outcome == "offer"]
    assert len(sent) > len(customers) / 2
    assert spent <= R.budget
    for d in sent:
        assert not failed(d.checks)


@pytest.mark.parametrize("rules", [Rules(max_pct=10, max_flat=100), Rules(margin_floor=25), Rules(quiet_from=18, quiet_to=11),
                                   Rules(budget=20_000), Rules(grid={s: ["points_reminder", "cart_reminder"] for s in R.grid})])
def test_stricter_rules_are_always_respected(customers, rules):
    decisions, spent = campaign(customers, rules)
    assert spent <= rules.budget
    for c, d in zip(customers, decisions):
        if d.offer:
            assert d.offer.pct <= rules.max_pct and d.offer.flat <= rules.max_flat
            assert not is_quiet(d.offer.send_hour, rules)
            assert d.offer.type in rules.grid[c["seg"]]
            assert not failed(d.checks)


def test_holdout_share_matches_the_rule(customers):
    share = sum(in_holdout(c, R) for c in customers) / len(customers)
    assert .07 < share < .13
    assert not any(in_holdout(c, Rules(holdout_pct=0)) for c in customers)


def test_blocked_customers_get_nothing_and_a_reason():
    d = decide(customer(opted_out=True), R)
    assert d.outcome == "blocked" and d.offer is None and "Stop offers" in d.reason


def test_thin_margin_favourite_moves_the_discount_to_another_category():
    c = customer(seg="at_risk", orders=[order(d, cat="electronics", value=3000) for d in (120, 150)] + [order(200, cat="fashion")],
                 pts_exp=0, last_offer_ago=99)
    c["disc_aff"] = .9
    d = decide(c, R, use_holdout=False, only=["pct_off"])
    assert d.offer.cat == "fashion" and "too thin" in d.reason


def test_cart_trigger_only_sends_a_cart_reminder():
    c = customer(cart=cart(("Yoga mat", 699, "sports"), hours_ago=2))
    d = decide(c, R, use_holdout=False, only=["cart_reminder"], now_hour=15)
    assert d.offer.type == "cart_reminder" and d.offer.pct == 0 and d.offer.send_hour == 15


def test_live_offer_at_night_is_moved_to_the_morning():
    c = customer(cart=cart(("Yoga mat", 699, "sports")))
    d = decide(c, R, use_holdout=False, only=["cart_reminder"], now_hour=23)
    assert (d.offer.send_hour, d.offer.send_day) == (9, 1)
    assert next_send_time(3, R) == (9, 0) and next_send_time(14, R) == (14, 0)


def test_offer_mix_is_varied(customers):
    decisions, _ = campaign(customers, R)
    mix = Counter(d.offer.type for d in decisions if d.offer)
    assert len(mix) >= 7 and max(mix.values()) / sum(mix.values()) < .4
