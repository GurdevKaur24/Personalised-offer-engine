"""What the engine knows about a customer: features worked out from their history, and their segment.

`customer_view` drops anything hidden (keys starting with "_", such as the persona), so the engine can't peek.
"""
import math
from statistics import median

from .catalog import CAT_KEYS, CATS, FESTIVE

SEGMENTS = {
    "champions": {"label": "Champions", "play": "Thank them with points and early access. They buy anyway, so discounts mostly lose margin."},
    "loyal": {"label": "Loyal", "play": "Keep them close with points and free delivery."},
    "new": {"label": "New", "play": "Win the second order with a small welcome offer."},
    "attention": {"label": "Needs attention", "play": "A gentle nudge on their favourite category."},
    "at_risk": {"label": "At risk", "play": "Win them back before they leave. This is where a discount pays off most."},
    "lost": {"label": "Lost", "play": "One win-back try, then stop messaging."},
    "bargain": {"label": "Bargain hunters", "play": "Flat ₹ off above a minimum order protects margin."},
}
SEG_KEYS = list(SEGMENTS)


def customer_view(raw: dict) -> dict:
    c = {k: v for k, v in raw.items() if not k.startswith("_")}
    o = c["orders"]
    c["total"] = len(o)
    c["recency"] = o[0]["d"] if o else None
    o365 = [x for x in o if x["d"] <= 365]
    c["f365"] = len(o365)
    c["m365"] = sum(x["value"] for x in o365)
    c["spend_all"] = sum(x["value"] for x in o)
    c["aov"] = round(c["spend_all"] / c["total"]) if o else 900
    gaps = [o[i]["d"] - o[i - 1]["d"] for i in range(1, len(o))]
    usual = median(gaps) if len(gaps) >= 2 else 365 / max(1, c["f365"])
    c["usual_gap"] = round(min(365, max(7, usual)))
    c["churn"] = 1 / (1 + math.exp(-2.2 * (c["recency"] / c["usual_gap"] - 1.8))) if o else None
    c["disc_aff"] = sum(x["disc"] for x in o) / len(o) if o else None
    c["return_rate"] = sum(x["ret"] for x in o) / len(o) if o else 0.0
    c["cod_share"] = sum(x["pay"] == "COD" for x in o) / len(o) if o else 0.0
    c["cat_spend"] = {k: sum(x["value"] for x in o if x["cat"] == k) for k in CAT_KEYS}
    counts = {k: sum(1 for x in o if x["cat"] == k) for k in CAT_KEYS}
    c["cat_aov"] = {k: round(c["cat_spend"][k] / counts[k]) if counts[k] else round(CATS[k]["price"] * c["aov"] / 1200) for k in CAT_KEYS}
    top = sorted((k for k in CAT_KEYS if c["cat_spend"][k] > 0), key=lambda k: -c["cat_spend"][k])
    if not top:
        seen = [x["cat"] for x in (c["cart"]["items"] if c["cart"] else [])] + [b["cat"] for b in c["browse"]]
        top = list(dict.fromkeys(seen))
    c["top_cats"] = top
    c["blend_margin"] = sum(c["cat_spend"][k] * CATS[k]["margin"] for k in CAT_KEYS) / c["spend_all"] if c["spend_all"] else .3
    c["festive_share"] = sum(FESTIVE[x["d"]] for x in o) / len(o) if o else 0.0
    if c["cart"]:
        c["cart"] = {**c["cart"], "margin": sum(x["price"] * CATS[x["cat"]]["margin"] for x in c["cart"]["items"]) / c["cart"]["value"]}
    c["seg"] = segment_of(c)
    return c


def segment_of(c: dict) -> str:
    if c["signup_ago"] <= 60 or (c["total"] <= 1 and c["signup_ago"] <= 120):
        return "new"
    if c["total"] == 0:
        return "attention"
    if c["recency"] > 180:
        return "lost"
    if c["churn"] >= .6 and c["total"] >= 3:
        return "at_risk"
    if c["f365"] >= 10 and c["recency"] <= 30:
        return "champions"
    if c["disc_aff"] >= .55 and c["total"] >= 3:
        return "bargain"
    if c["f365"] >= 5 and c["recency"] <= 60:
        return "loyal"
    return "attention"


def _ago(d: int) -> str:
    return "today" if d == 0 else "yesterday" if d == 1 else f"{d} days ago"


def _plural(n: int, w: str) -> str:
    return f"{n} {w}{'' if n == 1 else 's'}"


def why_segment(c: dict) -> str:
    s = c["seg"]
    if s == "new":
        return f"Joined {c['signup_ago']} days ago and has {_plural(c['total'], 'order')}."
    if s == "lost":
        return f"Last order was {c['recency']} days ago (more than 180)."
    if s == "at_risk":
        return f"Usually orders every {c['usual_gap']} days, but the last order was {c['recency']} days ago."
    if s == "champions":
        return f"{c['f365']} orders in the last 12 months, and bought {_ago(c['recency'])}."
    if s == "bargain":
        return f"{round(c['disc_aff'] * 100)}% of their orders used a coupon."
    if s == "loyal":
        return f"{c['f365']} orders in the last 12 months, last one {_ago(c['recency'])}."
    if c["total"] == 0:
        return f"Signed up {c['signup_ago']} days ago but has not ordered yet."
    return f"Buys now and then ({_plural(c['f365'], 'order')} in 12 months): not loyal yet, not at risk."
