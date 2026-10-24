"""Decide which offer one customer gets.

For now the choice is rule-based (a scored shortlist, safest values that fit the rules). The Claude agent will
choose from the same allowed offers later; whatever chooses, the checker has the final say.
"""
import math
import zlib
from dataclasses import dataclass, field
from datetime import date

from .catalog import CAT_KEYS, CATS, DELIVERY_COST, NOW_HOUR, TODAY
from .checker import Check, allowed_offers, check_customer, check_offer, failed, is_quiet, max_pct_by_margin
from .features import SEGMENTS
from .offers import Offer, make_offer
from .rules import Rules


@dataclass
class Decision:
    outcome: str                         # "offer", "holdout", "blocked" or "no_offer"
    offer: Offer | None = None
    checks: list[Check] = field(default_factory=list)
    reason: str = ""


def in_holdout(c: dict, r: Rules) -> bool:
    return zlib.crc32(f"{c['id']}holdout".encode()) % 100 < r.holdout_pct


def next_send_time(hour: int, r: Rules) -> tuple[int, int]:
    """(hour, day offset) of the first moment at or after `hour` that is outside quiet hours."""
    if not is_quiet(hour, r):
        return hour, 0
    tomorrow = r.quiet_from > r.quiet_to and hour >= r.quiet_from
    return r.quiet_to, 1 if tomorrow else 0


def _round(x: float, step: int) -> int:
    return round(x / step) * step


def _min_order_for_margin(cost: int, margin: float, r: Rules) -> int | None:
    """Smallest ₹…99 order that keeps the margin floor after `cost`; None if no order size can."""
    room = margin - r.margin_floor / 100
    return math.ceil(cost / room / 100) * 100 - 1 if room > .01 else None


def _score(c: dict) -> dict[str, float]:
    churn, disc = c["churn"] or 0, c["disc_aff"] or 0
    return {
        "cart_reminder": 100,
        "welcome": 85,
        "win_back": 80,
        "points_reminder": 55 + min(30, c["pts_exp"] / 10),
        "pct_off": 15 + 60 * disc + 20 * churn,
        "flat_off": 20 + 50 * disc + (10 if c["aov"] > 1500 else 0),
        "free_delivery": 30 + (25 if c["tier"] == 3 else 0) + (15 if c["aov"] < 900 else 0) + (5 if c["cod_share"] > .4 else 0),
        "double_points": 30 + (25 if c["f365"] >= 5 else 0) + (10 if c["points"] > 300 else 0),
        "early_access": 35 + (30 if c["seg"] == "champions" else 0) + (15 if c["festive_share"] > .4 else 0),
    }


def _values(c: dict, t: str, r: Rules) -> dict | None:
    """Offer values that fit the rules for this customer, or None if this type can't work for them."""
    if t == "pct_off":
        want = max(5, _round(5 + 12 * (c["churn"] or .3) + 10 * (c["disc_aff"] or .3), 5))
        for cat in c["top_cats"] + CAT_KEYS:          # favourite category first, if its margin allows a discount
            pct = min(r.max_pct, want, max_pct_by_margin(CATS[cat]["margin"], r) // 5 * 5)
            if pct >= 5:
                return {"cat": cat, "pct": pct}
        return None
    if t == "win_back":
        pct = min(r.max_pct, 15, max_pct_by_margin(c["blend_margin"], r) // 5 * 5)
        return {"pct": pct} if pct >= 5 else None
    if t in ("flat_off", "welcome"):
        flat = min(r.max_flat, r.welcome_flat) if t == "welcome" else min(r.max_flat, max(50, _round(c["aov"] * .1, 50)))
        need = _min_order_for_margin(flat, c["blend_margin"], r)
        if flat <= 0 or need is None:
            return None
        base = 499 if t == "welcome" else max(299, _round(c["aov"] * 1.2, 100) - 1)
        return {"flat": flat, "min_order": max(base, need)}
    if t == "free_delivery":
        need = _min_order_for_margin(DELIVERY_COST, c["blend_margin"], r)
        if need is None:
            return None
        return {"min_order": max(499 if c["aov"] < 500 else 0, need if c["aov"] < need else 0)}
    if t == "cart_reminder":
        pct = 0
        if c["cart"]["hours_ago"] > 24 and (c["disc_aff"] or 0) > .4:
            pct = min(r.cart_max_pct, r.max_pct, max_pct_by_margin(c["cart"]["margin"], r))
        return {"pct": pct}
    return {}


def why_offer(c: dict, o: Offer) -> str:
    fav = CATS[c["top_cats"][0]]["name"] if c["top_cats"] else "new arrivals"
    if o.type == "cart_reminder":
        h = c["cart"]["hours_ago"]
        when = f"{h} hours" if h < 24 else f"{round(h / 24)} days"
        return f"Left ₹{c['cart']['value']:,} in the cart {when} ago" + (", and often waits for a coupon, so a small discount." if o.pct else "; a reminder alone often brings them back.")
    if o.type == "welcome":
        return f"New customer with {c['total']} order(s); the second order is the hardest to win."
    if o.type == "win_back":
        return f"No order for {c['recency']} days. One clear win-back offer before we stop messaging."
    if o.type == "points_reminder":
        return f"{c['pts_exp']} points expire within 30 days; a reminder costs nothing."
    if o.type == "pct_off":
        where = f"Likes {fav}, so the discount is there." if o.cat == (c["top_cats"] or [None])[0] else \
                f"Likes {fav}, but its margin is too thin for a discount, so the offer is on {CATS[o.cat]['name']}."
        return f"Usually orders every {c['usual_gap']} days, last order {c['recency']} days ago. {where}"
    if o.type == "flat_off":
        return f"Uses coupons on {(c['disc_aff'] or 0):.0%} of orders. Flat ₹ off above ₹{o.min_order:,} lifts the basket and protects margin."
    if o.type == "free_delivery":
        return ("Smaller city, " if c["tier"] == 3 else "") + f"average order ₹{c['aov']:,}; delivery charges put off small orders."
    if o.type == "double_points":
        return f"{c['f365']} orders this year and {c['points']} points. Rewards matter more to them than discounts."
    return f"{SEGMENTS[c['seg']]['label']}: would buy anyway, so a perk instead of a discount keeps margin."


def decide(c: dict, r: Rules, spent: int = 0, *, now_hour: int = NOW_HOUR, today: date = TODAY,
           only: list[str] | None = None, use_holdout: bool = True) -> Decision:
    """The best allowed offer that passes every rule, or why there is none.

    `only` limits the offer types (e.g. ["cart_reminder"] for a live cart trigger).
    The offer is timed for the customer's usual hour in a campaign, or for now in a live trigger
    (pass now_hour); either way it is moved out of quiet hours.
    """
    cust = check_customer(c, r, cart_trigger=only == ["cart_reminder"])
    bad = failed(cust)
    if bad:
        return Decision("blocked", checks=cust, reason=bad[0].detail)
    if use_holdout and in_holdout(c, r):
        return Decision("holdout", checks=cust, reason="Kept out on purpose so we can measure what the offers add.")
    types = [t for t in allowed_offers(c, r) if only is None or t in only]
    scores = _score(c)
    last_checks: list[Check] = []
    for t in sorted(types, key=lambda t: -scores[t]):
        vals = _values(c, t, r)
        if vals is None:
            continue
        hour, day = next_send_time(now_hour, r)
        o = make_offer(c, t, r, send_hour=hour, send_day=day, today=today, **vals)
        o.reason = why_offer(c, o)
        checks = check_offer(c, o, r, spent)
        if not failed(checks):
            return Decision("offer", o, cust + checks, o.reason)
        last_checks = checks
    if last_checks:
        return Decision("no_offer", checks=cust + last_checks, reason=failed(last_checks)[0].detail)
    return Decision("no_offer", checks=cust, reason="No offer type is allowed for this customer right now.")
