"""The rule checker: the source of truth for "safe to send".

Nothing is sent unless `check_customer` and `check_offer` both pass. The AI's choices go through the same checks
as everything else, so a limit holds even if the AI ignores it.
"""
from dataclasses import dataclass

from .catalog import LANGS
from .features import SEGMENTS
from .messages import script_lang
from .offers import Offer
from .rules import OFFER_TYPES, Rules

CHECKS = {
    "optout":   ("Has not stopped offers", "Customer stopped offers"),
    "recent":   ("Did not buy very recently", "Bought very recently"),
    "returns":  ("Return rate within limit", "Returns too many orders"),
    "weekcap":  ("Weekly offer limit", "Already got enough offers this week"),
    "gap":      ("Days since last offer", "Got an offer too recently"),
    "allowed":  ("Offer allowed for this segment", "Offer type not allowed for the segment"),
    "discount": ("Discount within limit", "Discount above the limit"),
    "margin":   ("Margin floor", "Would break the margin floor"),
    "budget":   ("Campaign budget", "Not enough budget left"),
    "quiet":    ("Quiet hours", "Planned during quiet hours"),
    "expiry":   ("Expiry date", "Expiry missing or too long"),
    "words":    ("Banned words", "Message used a banned word"),
    "length":   ("Message length", "Message too long"),
    "language": ("Customer's language", "Message not in the customer's language"),
}
CUSTOMER_CHECKS = ["optout", "recent", "returns", "weekcap", "gap"]
OFFER_CHECKS = ["allowed", "discount", "margin", "budget", "quiet", "expiry", "words", "length", "language"]
MARGIN_TOLERANCE = .0005          # rupee rounding of the discount must not fail an offer that is exactly at the floor


@dataclass
class Check:
    id: str
    ok: bool
    detail: str

    @property
    def label(self) -> str:
        return CHECKS[self.id][0]


def failed(checks: list[Check]) -> list[Check]:
    return [x for x in checks if not x.ok]


def hour_label(h: int) -> str:
    h %= 24
    return f"{h % 12 or 12} {'am' if h < 12 else 'pm'}"


def _plural(n: int, w: str) -> str:
    return f"{n} {w}{'' if n == 1 else 's'}"


def is_quiet(hour: int, r: Rules) -> bool:
    if r.quiet_from == r.quiet_to:
        return False
    if r.quiet_from > r.quiet_to:                          # wraps past midnight, e.g. 9 pm to 9 am
        return hour >= r.quiet_from or hour < r.quiet_to
    return r.quiet_from <= hour < r.quiet_to


def max_pct_by_margin(margin: float, r: Rules) -> int:
    """Biggest whole % off that still keeps the margin floor."""
    return max(0, int((margin - r.margin_floor / 100) * 100 + 1e-9))


def allowed_offers(c: dict, r: Rules) -> list[str]:
    """Offer types this customer may get right now: ticked for their segment, and making sense for them."""
    def fits(t: str) -> bool:
        if t == "cart_reminder":
            return bool(c["cart"])
        if t == "points_reminder":
            return c["pts_exp"] >= 50
        if t == "welcome":
            return c["total"] <= 1 and r.max_flat > 0
        if t in ("pct_off", "win_back"):
            return r.max_pct > 0
        if t == "flat_off":
            return r.max_flat > 0
        return True
    return [t for t in r.grid.get(c["seg"], []) if fits(t)]


def check_customer(c: dict, r: Rules, cart_trigger: bool = False) -> list[Check]:
    """`cart_trigger`: the customer just left a cart. With the cart_own_limit rule on, the weekly limit and the gap
    between offers don't apply (the caller sends at most one reminder per cart)."""
    rec = c["recency"]
    own = cart_trigger and r.cart_own_limit
    checks = [
        Check("optout", not c["opted_out"], 'Tapped "Stop offers" earlier.' if c["opted_out"] else "Still happy to get offers."),
        Check("recent", rec is None or rec >= r.skip_recent_days,
              f"Bought {'today' if rec == 0 else 'yesterday' if rec == 1 else f'{rec} days ago'}; the rule skips anyone who bought in the last {_plural(r.skip_recent_days, 'day')}."
              if rec is not None and rec < r.skip_recent_days else f"No order in the last {_plural(r.skip_recent_days, 'day')}."),
        Check("returns", c["total"] < 3 or c["return_rate"] * 100 <= r.max_return_pct,
              f"Returns {c['return_rate']:.0%} of orders (limit {r.max_return_pct}%)."),
        Check("weekcap", c["offers_this_week"] < r.max_per_week,
              f"{_plural(c['offers_this_week'], 'offer')} this week (limit {r.max_per_week})."),
        Check("gap", c["last_offer_ago"] >= r.min_gap_days,
              "No recent offers." if c["last_offer_ago"] >= 99 else f"Last offer {c['last_offer_ago']} days ago (needs {_plural(r.min_gap_days, 'day')} in between)."),
    ]
    if own:
        for x in checks:
            if x.id in ("weekcap", "gap") and not x.ok:
                x.ok, x.detail = True, f"{x.detail[:-1]}, but cart reminders have their own limit: one per cart."
    return checks


def check_offer(c: dict, o: Offer, r: Rules, spent: int = 0) -> list[Check]:
    if o.type == "cart_reminder":
        lim = min(r.cart_max_pct, r.max_pct)
        disc = (o.pct <= lim, f"Cart discount {o.pct}% (limit {lim}%).")
    elif o.type in ("pct_off", "win_back"):
        disc = (o.pct <= r.max_pct, f"Discount {o.pct}% (limit {r.max_pct}%).")
    elif o.type in ("flat_off", "welcome"):
        disc = (o.flat <= r.max_flat, f"₹{o.flat} off (limit ₹{r.max_flat}).")
    else:
        disc = (True, "No price discount.")
    text = o.text.lower()
    banned = next((w for w in r.banned if w and w.lower() in text), None)
    wrote = script_lang(o.text)
    expiry_shown = o.expiry_label in o.text
    expiry_ok = 2 <= o.expiry_days <= r.expiry_days and (not r.require_expiry or expiry_shown)
    expiry_note = (", expiry date shown." if expiry_shown else ", but the message does not show the expiry date.") if r.require_expiry else "."
    seg_label = SEGMENTS[c["seg"]]["label"]
    return [
        Check("allowed", o.type in r.grid.get(c["seg"], []), f"{OFFER_TYPES[o.type]['label']} for {seg_label}."),
        Check("discount", *disc),
        Check("margin", o.cost == 0 or o.margin_after >= r.margin_floor / 100 - MARGIN_TOLERANCE,
              "Costs nothing, so margin is unchanged." if o.cost == 0
              else f"Leaves {o.margin_after:.0%} margin on a ₹{o.eff:,} order (floor {r.margin_floor}%)."),
        Check("budget", spent + o.cost <= r.budget, f"Costs up to ₹{o.cost:,}; ₹{max(0, r.budget - spent):,} of the budget left."),
        Check("quiet", not is_quiet(o.send_hour, r),
              f"Sends {'tomorrow' if o.send_day else 'today'} at {hour_label(o.send_hour)} (quiet hours {hour_label(r.quiet_from)} to {hour_label(r.quiet_to)})."),
        Check("expiry", expiry_ok, f"Valid for {_plural(o.expiry_days, 'day')} (2 to {r.expiry_days} allowed){expiry_note}"),
        Check("words", banned is None, f'Uses "{banned}".' if banned else "No banned words."),
        Check("length", len(o.text) <= r.max_chars, f"{len(o.text)} characters (limit {r.max_chars})."),
        Check("language", wrote == c["lang"], f"Written in {LANGS[wrote]}; customer reads {LANGS[c['lang']]}."),
    ]


def safe_to_send(c: dict, o: Offer, r: Rules, spent: int = 0) -> bool:
    return not failed(check_customer(c, r)) and not failed(check_offer(c, o, r, spent))
