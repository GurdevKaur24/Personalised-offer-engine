"""Every rule the marketing team sets is enforced by the checker, one test (or more) per rule."""
import pytest

from helpers import cart, customer, order
from peshkash.checker import (CUSTOMER_CHECKS, OFFER_CHECKS, allowed_offers, check_customer, check_offer, failed,
                              is_quiet, max_pct_by_margin, safe_to_send)
from peshkash.messages import script_lang
from peshkash.offers import make_offer
from peshkash.rules import OFFER_KEYS, Rules

R = Rules()


def result(checks, check_id):
    return next(x for x in checks if x.id == check_id)


def offer_ok(c, o, check_id, rules=R, spent=0):
    return result(check_offer(c, o, rules, spent), check_id).ok


def test_checks_come_back_in_a_fixed_order():
    c = customer()
    assert [x.id for x in check_customer(c, R)] == CUSTOMER_CHECKS
    assert [x.id for x in check_offer(c, make_offer(c, "double_points", R, send_hour=19), R)] == OFFER_CHECKS


# ---------- Customer rules ----------
def test_customers_who_stopped_offers_are_skipped():
    assert not result(check_customer(customer(opted_out=True), R), "optout").ok
    assert result(check_customer(customer(), R), "optout").ok


@pytest.mark.parametrize("last_order, ok", [(0, False), (2, False), (3, True), (40, True)])
def test_recent_buyers_are_skipped(last_order, ok):
    c = customer(orders=[order(last_order), order(60), order(90)])
    assert result(check_customer(c, R), "recent").ok is ok


def test_customers_who_never_ordered_pass_the_recent_rule():
    assert result(check_customer(customer(orders=[]), R), "recent").ok


def test_heavy_returners_are_skipped_but_only_with_enough_orders():
    heavy = customer(orders=[order(10, ret=True), order(40, ret=True), order(70)])            # 67% returned
    assert not result(check_customer(heavy, R), "returns").ok
    two_orders = customer(orders=[order(10, ret=True), order(40, ret=True)])                  # too few to judge
    assert result(check_customer(two_orders, R), "returns").ok
    assert result(check_customer(heavy, Rules(max_return_pct=70)), "returns").ok


@pytest.mark.parametrize("this_week, ok", [(0, True), (1, True), (2, False), (3, False)])
def test_weekly_offer_limit(this_week, ok):
    assert result(check_customer(customer(offers_this_week=this_week), R), "weekcap").ok is ok


def test_cart_reminders_can_have_their_own_limit():
    c = customer(offers_this_week=2, last_offer_ago=0)
    assert not any(x.ok for x in check_customer(c, R) if x.id in ("weekcap", "gap"))
    assert all(x.ok for x in check_customer(c, R, cart_trigger=True) if x.id in ("weekcap", "gap"))
    assert not any(x.ok for x in check_customer(c, Rules(cart_own_limit=False), cart_trigger=True) if x.id in ("weekcap", "gap"))
    assert not result(check_customer(customer(opted_out=True), R, cart_trigger=True), "optout").ok   # stopping always wins


@pytest.mark.parametrize("days, ok", [(0, False), (2, False), (3, True), (99, True)])
def test_days_between_offers(days, ok):
    assert result(check_customer(customer(last_offer_ago=days), R), "gap").ok is ok


# ---------- Offer rules ----------
def test_offer_type_must_be_ticked_for_the_segment():
    champ = customer(seg="champions")
    assert not offer_ok(champ, make_offer(champ, "pct_off", R, pct=10, send_hour=19), "allowed")
    assert offer_ok(champ, make_offer(champ, "double_points", R, send_hour=19), "allowed")


@pytest.mark.parametrize("type, kw, ok", [
    ("pct_off", {"pct": 20}, True), ("pct_off", {"pct": 25}, False),
    ("win_back", {"pct": 20}, True), ("win_back", {"pct": 21}, False),
    ("flat_off", {"flat": 300, "min_order": 2999}, True), ("flat_off", {"flat": 350, "min_order": 2999}, False),
    ("welcome", {"flat": 301, "min_order": 2999}, False),
])
def test_discount_limits(type, kw, ok):
    c = customer(seg="at_risk")
    assert offer_ok(c, make_offer(c, type, R, send_hour=19, **kw), "discount") is ok


def test_cart_discount_has_its_own_smaller_limit_and_never_beats_the_main_one():
    c = customer(cart=cart(("Cotton kurta set", 1299, "fashion")))
    assert offer_ok(c, make_offer(c, "cart_reminder", R, pct=5, send_hour=19), "discount")
    assert not offer_ok(c, make_offer(c, "cart_reminder", R, pct=6, send_hour=19), "discount")
    assert not offer_ok(c, make_offer(c, "cart_reminder", Rules(max_pct=3), pct=5, send_hour=19), "discount", Rules(max_pct=3))


def test_margin_floor_blocks_discounts_on_thin_margin_categories():
    c = customer(seg="at_risk", orders=[order(d, cat="electronics", value=3000) for d in (90, 120, 150)])
    assert max_pct_by_margin(.12, R) == 2
    assert not offer_ok(c, make_offer(c, "pct_off", R, cat="electronics", pct=10, send_hour=19), "margin")
    assert offer_ok(c, make_offer(c, "pct_off", R, cat="fashion", pct=30, send_hour=19), "margin")


def test_an_offer_exactly_at_the_floor_passes_despite_rupee_rounding():
    c = customer(seg="at_risk", orders=[order(d, value=1299) for d in (90, 120, 150)])       # fashion, 45% margin
    o = make_offer(c, "pct_off", R, cat="fashion", pct=35, send_hour=19)
    assert o.margin_after < .10                                                             # 455/1299 rounds just under
    assert offer_ok(c, o, "margin")
    assert not offer_ok(c, make_offer(c, "pct_off", R, cat="fashion", pct=36, send_hour=19), "margin")


def test_raising_the_minimum_order_can_rescue_a_flat_discount():
    c = customer(seg="bargain", orders=[order(d, cat="grocery", value=700) for d in (30, 60, 90)])   # 18% margin
    assert not offer_ok(c, make_offer(c, "flat_off", R, flat=100, min_order=699, send_hour=19), "margin")
    assert offer_ok(c, make_offer(c, "flat_off", R, flat=100, min_order=1299, send_hour=19), "margin")


@pytest.mark.parametrize("type", ["points_reminder", "early_access", "cart_reminder"])
def test_free_offers_never_break_the_margin_floor(type):
    c = customer(seg="champions", orders=[order(d, cat="electronics", value=3000) for d in (5, 20, 40)],
                 cart=cart(("5G phone", 13999, "electronics")))
    o = make_offer(c, type, Rules(margin_floor=60), send_hour=19)
    assert o.cost == 0 and offer_ok(c, o, "margin", Rules(margin_floor=60))


def test_budget_counts_the_full_cost_and_free_offers_still_fit():
    c = customer(seg="at_risk")
    o = make_offer(c, "pct_off", R, pct=20, send_hour=19)
    assert offer_ok(c, o, "budget", spent=R.budget - o.cost)
    assert not offer_ok(c, o, "budget", spent=R.budget - o.cost + 1)
    assert offer_ok(c, make_offer(c, "points_reminder", R, send_hour=19), "budget", spent=R.budget)


@pytest.mark.parametrize("hour, quiet", [(8, True), (9, False), (12, False), (20, False), (21, True), (23, True), (0, True)])
def test_quiet_hours_wrap_past_midnight(hour, quiet):
    assert is_quiet(hour, R) is quiet
    c = customer()
    assert offer_ok(c, make_offer(c, "double_points", R, send_hour=hour), "quiet") is not quiet


def test_quiet_hours_inside_the_day_and_switched_off():
    assert is_quiet(14, Rules(quiet_from=13, quiet_to=15)) and not is_quiet(15, Rules(quiet_from=13, quiet_to=15))
    assert not any(is_quiet(h, Rules(quiet_from=0, quiet_to=0)) for h in range(24))


@pytest.mark.parametrize("kw, rules, ok", [
    ({}, R, True),
    ({"expiry_days": 15}, R, False),                         # "valid till Diwali" is longer than allowed
    ({"expiry_days": 1}, R, False),                          # too short to be fair
    ({"no_expiry": True}, R, False),                         # message forgot the date
    ({"no_expiry": True}, Rules(require_expiry=False), True),
])
def test_expiry_rules(kw, rules, ok):
    c = customer()
    assert offer_ok(c, make_offer(c, "double_points", rules, send_hour=19, **kw), "expiry", rules) is ok


def test_banned_words_are_caught_in_any_case():
    c = customer()
    assert not offer_ok(c, make_offer(c, "double_points", R, send_hour=19, extra_line="GUARANTEED lowest price!"), "words")
    assert offer_ok(c, make_offer(c, "double_points", R, send_hour=19), "words")
    assert not offer_ok(c, make_offer(c, "double_points", R, send_hour=19), "words", Rules(banned=["points"]))


def test_message_length_limit():
    c = customer()
    o = make_offer(c, "double_points", R, send_hour=19)
    assert offer_ok(c, o, "length")
    assert not offer_ok(c, o, "length", Rules(max_chars=len(o.text) - 1))


@pytest.mark.parametrize("cust_lang, written, ok", [("pa", "pa", True), ("pa", "en", False), ("hi", "hi", True), ("en", "hi", False)])
def test_message_must_be_in_the_customers_language(cust_lang, written, ok):
    c = customer(lang=cust_lang)
    assert offer_ok(c, make_offer(c, "double_points", R, send_hour=19, lang=written), "language") is ok


# ---------- Allowed offers ----------
def test_allowed_offers_follow_the_grid_and_the_customer():
    c = customer(seg="at_risk", pts_exp=10)
    assert allowed_offers(c, R) == ["pct_off", "flat_off", "free_delivery"]          # no cart, too few points
    c = customer(seg="at_risk", pts_exp=80, cart=cart(("Yoga mat", 699, "sports")))
    assert allowed_offers(c, R) == ["pct_off", "flat_off", "free_delivery", "points_reminder", "cart_reminder"]
    assert "pct_off" not in allowed_offers(c, Rules(max_pct=0))
    assert allowed_offers(c, Rules(grid={"at_risk": []})) == []


def test_welcome_offer_is_only_for_first_or_second_order():
    assert "welcome" in allowed_offers(customer(seg="new", orders=[order(10)]), R)
    assert "welcome" not in allowed_offers(customer(seg="new", orders=[order(10), order(30)]), R)


# ---------- Messages ----------
@pytest.mark.parametrize("lang", ["en", "hi", "pa"])
@pytest.mark.parametrize("type", OFFER_KEYS)
def test_every_offer_renders_in_every_language(type, lang):
    c = customer(seg="loyal", lang=lang, cart=cart(("Yoga mat", 699, "sports")))
    o = make_offer(c, type, R, send_hour=19, pct=10, flat=100, min_order=999)
    assert o.code in o.text and o.expiry_label in o.text
    assert script_lang(o.text) == lang
    assert "{" not in o.text and len(o.text.splitlines()) == 3


# ---------- Whole data set ----------
def test_free_offers_at_a_normal_hour_pass_for_every_eligible_customer(customers):
    """The checker must not be stricter than the rules: harmless offers always get through."""
    checked = 0
    for c in customers:
        if failed(check_customer(c, R)):
            continue
        for t in ("points_reminder", "early_access", "cart_reminder"):
            if t in allowed_offers(c, R):
                o = make_offer(c, t, R, send_hour=19)
                assert safe_to_send(c, o, R), [x.detail for x in failed(check_offer(c, o, R))]
                checked += 1
    assert checked > 300


def test_customer_rules_block_a_sensible_share(customers):
    blocked = sum(1 for c in customers if failed(check_customer(c, R)))
    assert .1 < blocked / len(customers) < .4
