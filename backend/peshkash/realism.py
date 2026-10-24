"""Does the synthetic data behave like real shoppers? Each check compares one pattern with what real
Indian e-commerce data shows. Used by the tests, the generator's summary and (later) the overview screen.
"""
from dataclasses import dataclass
from statistics import mean, median

from .catalog import CAT_KEYS, CATS, date_ago


@dataclass
class RealismCheck:
    key: str
    label: str
    value: float
    shown: str
    expected: str
    ok: bool


def realism_report(customers: list[dict]) -> list[RealismCheck]:
    """`customers` are raw generated customers (or views; only raw fields are read)."""
    orders = [o for c in customers for o in c["orders"]]
    checks: list[RealismCheck] = []

    def add(key, label, value, shown, expected, ok):
        checks.append(RealismCheck(key, label, value, shown, expected, ok))

    spends = sorted((sum(o["value"] for o in c["orders"]) for c in customers), reverse=True)
    top20 = sum(spends[:round(len(spends) * .2)]) / sum(spends)
    add("pareto", "Top 20% of customers bring this share of revenue", top20, f"{top20:.0%}", "60–80%", .6 <= top20 <= .8)

    o90 = sum(1 for o in orders if o["d"] <= 90)
    abandoned = sum(c["abandoned90"] for c in customers)
    rate = abandoned / (abandoned + o90)
    add("abandon", "Carts left without buying (last 90 days)", rate, f"{rate:.0%}", "65–80%", .65 <= rate <= .8)

    by_month: dict[tuple, int] = {}
    for o in orders:
        dt = date_ago(o["d"])
        by_month[(dt.year, dt.month)] = by_month.get((dt.year, dt.month), 0) + o["value"]
    full = [v for k, v in by_month.items() if (2025, 5) <= k <= (2026, 9)]
    lift = by_month.get((2025, 10), 0) / mean(full)
    add("festive", "Festive month (Oct 2025) revenue vs an average month", lift, f"{lift:.1f}×", "at least 1.5×", lift >= 1.5)

    dom_orders, dom_days, wk_orders, wk_days = [0] * 32, [0] * 32, [0, 0], [0, 0]
    for d in range(540):
        dt = date_ago(d)
        dom_days[dt.day] += 1
        wk_days[dt.weekday() >= 5] += 1
    for o in orders:
        if o["d"] < 540:
            dt = date_ago(o["d"])
            dom_orders[dt.day] += 1
            wk_orders[dt.weekday() >= 5] += 1
    per_dom = [dom_orders[i] / dom_days[i] if dom_days[i] else 0 for i in range(32)]
    salary = mean(per_dom[1:6]) / mean(per_dom[6:])
    add("salary", "Orders per day on salary days (1st–5th) vs other days", salary, f"{salary:.2f}×", "above 1.1×", salary > 1.1)
    weekend = (wk_orders[1] / wk_days[1]) / (wk_orders[0] / wk_days[0])
    add("weekend", "Orders per day at weekends vs weekdays", weekend, f"{weekend:.2f}×", "above 1.1×", weekend > 1.1)

    def cod(tier):
        os = [o for c in customers if c["tier"] == tier for o in c["orders"]]
        return sum(o["pay"] == "COD" for o in os) / len(os)
    cod1, cod3 = cod(1), cod(3)
    add("cod", "Cash on delivery: small cities vs big cities", cod3 - cod1, f"{cod3:.0%} vs {cod1:.0%}", "higher in small cities", cod3 > cod1)

    ret = {k: (sum(o["ret"] for o in orders if o["cat"] == k) / max(1, sum(1 for o in orders if o["cat"] == k))) for k in CAT_KEYS}
    worst = max(ret, key=ret.get)
    add("returns", "Category with the most returns", ret[worst], f"{CATS[worst]['name']} ({ret[worst]:.0%})", "Fashion", worst == "fashion")

    vals = [o["value"] for o in orders]
    skew = mean(vals) / median(vals)
    add("skew", "Average order vs typical (median) order", skew, f"{skew:.2f}×", "above 1.15× (a few big orders)", skew > 1.15)

    never = sum(1 for c in customers if not c["orders"]) / len(customers)
    add("never", "Signed up but never ordered", never, f"{never:.0%}", "5–25%", .05 <= never <= .25)
    return checks
