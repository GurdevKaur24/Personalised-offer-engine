"""One offer for one customer: value, cost to the business, timing, coupon code and message."""
import zlib
from dataclasses import dataclass, field
from datetime import date, timedelta

from .catalog import CATS, DELIVERY_COST, NOW_HOUR, TODAY
from .messages import fmt_date, render_message
from .rules import Rules


@dataclass
class Offer:
    type: str
    cat: str | None = None
    pct: int = 0
    flat: int = 0
    min_order: int = 0
    pts: int = 0
    send_hour: int = 0
    send_day: int = 0              # 0 = today, 1 = tomorrow
    expiry_days: int = 7
    lang: str = "en"
    basket: int = 0                # expected order value the offer applies to
    margin: float = 0.0            # margin on that order before the offer
    eff: int = 0                   # order value after any minimum order
    cost: int = 0                  # cost to us if the customer uses it
    margin_after: float = 0.0
    code: str = ""
    expiry_date: date = field(default=TODAY)
    expiry_label: str = ""
    text: str = ""
    reason: str = ""


def cost_of(o: Offer) -> int:
    if o.type in ("pct_off", "win_back", "cart_reminder"):
        return round(o.pct / 100 * o.eff)
    if o.type in ("flat_off", "welcome"):
        return o.flat
    if o.type == "free_delivery":
        return DELIVERY_COST
    if o.type == "double_points":
        return round(o.eff / 50)      # one extra point per ₹50, worth ₹1
    return 0                          # reminders and early access cost nothing


def coupon_code(c: dict, o: Offer) -> str:
    abbr = {"pct_off": (o.cat or "deal")[:4].upper(), "flat_off": "FLAT", "welcome": "HELLO", "free_delivery": "SHIP",
            "double_points": "2XPTS", "points_reminder": "PTS", "cart_reminder": "CART", "early_access": "EARLY", "win_back": "BACK"}[o.type]
    n, suffix = zlib.crc32(f"{c['id']}{o.type}".encode()), ""
    for _ in range(3):
        n, r = divmod(n, 36)
        suffix += "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"[r]
    return f"BK{abbr}{o.pct or o.flat or ''}-{suffix}"


def make_offer(c: dict, type: str, rules: Rules, *, cat: str | None = None, pct: int = 0, flat: int = 0, min_order: int = 0,
               send_hour: int | None = None, send_day: int | None = None, expiry_days: int | None = None,
               lang: str | None = None, no_expiry: bool = False, extra_line: str = "", reason: str = "",
               today: date = TODAY, custom_lines: tuple[str, str] | None = None) -> Offer:
    """Build an offer for a customer view `c`. Nothing here checks the rules; that is the checker's job."""
    o = Offer(type=type, pct=pct, flat=flat, min_order=min_order, lang=lang or c["lang"], reason=reason,
              expiry_days=rules.expiry_days if expiry_days is None else expiry_days)
    if type == "pct_off":
        o.cat = cat or (c["top_cats"][0] if c["top_cats"] else "fashion")
    if type == "cart_reminder":
        o.basket, o.margin = c["cart"]["value"], c["cart"]["margin"]
    elif o.cat:
        o.basket, o.margin = c["cat_aov"][o.cat], CATS[o.cat]["margin"]
    else:
        o.basket, o.margin = c["aov"], c["blend_margin"]
    if type == "points_reminder":
        o.pts = c["pts_exp"]
    o.eff = max(o.basket, o.min_order)
    o.cost = cost_of(o)
    o.margin_after = o.margin - o.cost / o.eff
    o.send_hour = c["active_hour"] if send_hour is None else send_hour
    o.send_day = (1 if o.send_hour <= NOW_HOUR else 0) if send_day is None else send_day
    o.code = coupon_code(c, o)
    o.expiry_date = today + timedelta(days=o.send_day + o.expiry_days)
    o.expiry_label = fmt_date(o.expiry_date, o.lang)
    o.text = render_message(c, o, o.lang, no_expiry=no_expiry, extra_line=extra_line, custom_lines=custom_lines)
    return o


def describe(o: Offer) -> str:
    """Short English summary for marketers, e.g. "15% off Fashion"."""
    return {
        "pct_off": lambda: f"{o.pct}% off {CATS[o.cat]['name']}" if o.cat else f"{o.pct}% off",
        "win_back": lambda: f"{o.pct}% off next order",
        "flat_off": lambda: f"₹{o.flat} off above ₹{o.min_order}",
        "welcome": lambda: f"₹{o.flat} off above ₹{o.min_order}",
        "free_delivery": lambda: "Free delivery" + (f" above ₹{o.min_order}" if o.min_order else ""),
        "double_points": lambda: "2× points on next order",
        "points_reminder": lambda: f"Reminder: {o.pts} points expiring",
        "cart_reminder": lambda: "Cart reminder" + (f" + {o.pct}% off" if o.pct else ""),
        "early_access": lambda: "Early access to Diwali sale",
    }[o.type]()
