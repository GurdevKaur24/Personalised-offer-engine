"""Synthetic BazaarKart customers: orders, browsing, carts, points and offer history.

Same seed, same data. Each customer's hidden persona is stored apart from what the engine reads
(table `hidden_personas`, key `_persona` in memory) and is only used to simulate responses.

Run:  python -m peshkash.datagen --customers 2000 --out data/generated
"""
import argparse
import csv
import math
import random
import sqlite3
import sys
from pathlib import Path

from .catalog import (CAT_KEYS, CATS, CITIES, FESTIVE, FIRST_F, FIRST_M, HISTORY_DAYS, PERSONAS, SALES, SEASON,
                      SURNAMES, ago_of)

DEFAULT_SEED = 20261024
HOUR_WEIGHTS = {9: 4, 10: 5, 11: 4, 12: 5, 13: 7, 14: 5, 16: 4, 17: 6, 18: 9, 19: 12, 20: 13, 21: 6, 22: 4, 23: 2}


def _weighted(rng: random.Random, weights: dict):
    return rng.choices(list(weights), weights=list(weights.values()))[0]


def _poisson(rng: random.Random, lam: float) -> int:
    if lam <= 0:
        return 0
    if lam > 30:
        return max(0, round(rng.normalvariate(lam, math.sqrt(lam))))
    limit, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1


def _customer(rng: random.Random, i: int) -> dict:
    persona = _weighted(rng, {k: p["share"] for k, p in PERSONAS.items()})
    P = PERSONAS[persona]
    female = rng.random() < .48
    last = rng.choice(SURNAMES)
    if female and last == "Singh":
        last = "Kaur"
    first = rng.choice(FIRST_F if female else FIRST_M)
    city = _weighted(rng, {c: w for c, _, w in CITIES})
    tier = next(t for c, t, _ in CITIES if c == city)
    lang = _weighted(rng, {1: {"en": 6, "hi": 3, "pa": 1}, 2: {"en": 45, "hi": 25, "pa": 30}, 3: {"en": 30, "hi": 25, "pa": 45}}[tier])
    age = _weighted(rng, {"18–24": 24, "25–34": 38, "35–44": 24, "45+": 14})
    signup_ago = rng.randint(4, 70) if persona == "new_explorer" else round(min(1500, 100 + rng.gammavariate(1.5, 280)))
    active_end = rng.randint(45, 150) if persona == "at_risk" else rng.randint(190, 480) if persona == "lapsed" else 0
    per_year = P["per_year"] * rng.lognormvariate(0, .6)
    aov_mult = P["aov"] * rng.lognormvariate(0, .3)
    disc_aff = min(.95, max(.02, P["disc"] + rng.normalvariate(0, .1)))
    return_mult = 3.5 if rng.random() < .03 else rng.lognormvariate(0, .3)    # ~3% serial returners
    cat_share = {k: CATS[k]["share"] for k in CAT_KEYS}
    fav1 = _weighted(rng, cat_share)
    fav2 = fav1
    while fav2 == fav1:
        fav2 = _weighted(rng, cat_share)
    cat_w = {k: CATS[k]["share"] * (5 if k == fav1 else 2.5 if k == fav2 else 1) for k in CAT_KEYS}
    cod_p = {1: .18, 2: .32, 3: .5}[tier]
    start = min(signup_ago, HISTORY_DAYS)

    orders = []

    def add_order(d0: int, lo: int, hi: int):
        # Shoppers shift purchases a few days toward weekends, salary days and sales.
        near = {x: SEASON[x] ** 2 for x in range(max(lo, d0 - 3), min(hi, d0 + 3) + 1)}
        d = _weighted(rng, near) if near else d0
        cat = _weighted(rng, cat_w)
        value = max(99, round(CATS[cat]["price"] * aov_mult * rng.lognormvariate(-.1, .5) / 10) * 10 - 1)
        orders.append({
            "d": d, "cat": cat, "value": value,
            "disc": rng.random() < min(.95, disc_aff * (1.25 if FESTIVE[d] else 1)),
            "pay": "COD" if rng.random() < cod_p else "UPI" if rng.random() < .72 else "Card",
            "ret": rng.random() < min(.8, CATS[cat]["ret"] * return_mult),
        })

    if persona == "festive_only":
        # Buys mostly in festive sales, rarely otherwise.
        for f, t, _, is_f in SALES:
            if not is_f:
                continue
            w_from, w_to = ago_of(*f), ago_of(*t)
            a, b = min(w_from, start), max(w_to, active_end)
            if a < b:
                continue
            for _ in range(_poisson(rng, 1.7 * min(1, (a - b + 1) / (w_from - w_to + 1)))):
                add_order(rng.randint(b, a), b, a)
        for _ in range(_poisson(rng, .5 * start / 365)):
            add_order(rng.randint(active_end, start), active_end, start)
    else:
        # Gaps between orders follow a gamma distribution; sales, weekends and salary days squeeze them.
        mean_gap = 365 / per_year
        if persona == "new_explorer":
            t = start - rng.gammavariate(1, 6) if rng.random() < .75 else -1
        else:
            t = start - rng.random() * min(mean_gap, 90)
        while t >= 0 and t > active_end and len(orders) < 150:
            d = round(t)
            add_order(d, 0, start)
            t -= rng.gammavariate(2, mean_gap / 2) / SEASON[d]
    orders.sort(key=lambda o: o["d"])                       # most recent first

    # Loyalty points: 1 point per ₹50 on kept orders, worth ₹1 each, expire after 12 months.
    keep = .3 + rng.random() * .6
    earned = expiring = 0
    for o in orders:
        if not o["ret"] and o["d"] <= 365:
            p = o["value"] // 50
            earned += p
            if o["d"] >= 335:
                expiring += p

    sessions30 = _poisson(rng, P["browse"] * (1.3 if FESTIVE[0] else 1) * rng.lognormvariate(0, .4))
    recency = orders[0]["d"] if orders else None
    if sessions30:
        last_visit = min(29, int(rng.gammavariate(1, 30 / (sessions30 + 1))))
    else:
        last_visit = min(recency if recency is not None else 999, 30 + rng.randint(0, 90))
    orders90 = sum(1 for o in orders if o["d"] <= 90)
    abandoned90 = _poisson(rng, orders90 * 2.1 + sessions30 * .25)
    cart = None
    if sessions30 > 0 and rng.random() < P["cart_open"]:
        items = []
        for _ in range(rng.randint(1, 3)):
            cat = _weighted(rng, cat_w)
            name, price = rng.choice(CATS[cat]["items"])
            items.append({"name": name, "price": price, "cat": cat})
        hours_ago = rng.randint(1, 120)
        last_visit = min(last_visit, hours_ago // 24)
        cart = {"items": items, "value": sum(x["price"] for x in items), "hours_ago": hours_ago}
    browse = []
    for k in range(min(4, sessions30)):
        cat = _weighted(rng, cat_w)
        browse.append({"d": last_visit + k * rng.randint(0, 4), "cat": cat, "item": rng.choice(CATS[cat]["items"])[0]})

    last_offer_ago = int(rng.gammavariate(1.5, 8)) if rng.random() < .7 else 99
    offers_this_week = (2 if rng.random() < .2 else 1) if last_offer_ago < 7 else 0

    return {
        "id": f"C{10001 + i}", "first": first, "name": f"{first} {last}", "gender": "F" if female else "M", "age": age,
        "city": city, "tier": tier, "lang": lang, "signup_ago": signup_ago, "orders": orders,
        "sessions30": sessions30, "last_visit": last_visit, "abandoned90": abandoned90, "cart": cart, "browse": browse,
        "points": round(earned * keep), "pts_exp": round(expiring * keep),
        "last_offer_ago": last_offer_ago, "offers_this_week": offers_this_week,
        "opted_out": rng.random() < .025 + P["opt_risk"], "active_hour": int(_weighted(rng, HOUR_WEIGHTS)),
        "_persona": persona,                                 # hidden: never read by the engine
    }


def generate(n: int = 2000, seed: int = DEFAULT_SEED) -> list[dict]:
    rng = random.Random(seed)
    return [_customer(rng, i) for i in range(n)]


# ---------- Storage ----------
SCHEMA = """
CREATE TABLE customers (id TEXT PRIMARY KEY, first_name TEXT, name TEXT, gender TEXT, age_band TEXT, city TEXT,
  city_tier INTEGER, lang TEXT, signup_days_ago INTEGER, sessions_30d INTEGER, last_visit_days_ago INTEGER,
  abandoned_carts_90d INTEGER, points INTEGER, points_expiring_30d INTEGER, last_offer_days_ago INTEGER,
  offers_this_week INTEGER, opted_out INTEGER, active_hour INTEGER);
CREATE TABLE orders (customer_id TEXT, days_ago INTEGER, category TEXT, value INTEGER, used_coupon INTEGER,
  payment TEXT, returned INTEGER);
CREATE TABLE cart_items (customer_id TEXT, name TEXT, price INTEGER, category TEXT, hours_ago INTEGER);
CREATE TABLE browsing (customer_id TEXT, days_ago INTEGER, category TEXT, item TEXT);
CREATE TABLE hidden_personas (customer_id TEXT PRIMARY KEY, persona TEXT);  -- simulation only, never read by the engine
"""
CUSTOMER_COLS = [("id", "id"), ("first", "first_name"), ("name", "name"), ("gender", "gender"), ("age", "age_band"),
                 ("city", "city"), ("tier", "city_tier"), ("lang", "lang"), ("signup_ago", "signup_days_ago"),
                 ("sessions30", "sessions_30d"), ("last_visit", "last_visit_days_ago"), ("abandoned90", "abandoned_carts_90d"),
                 ("points", "points"), ("pts_exp", "points_expiring_30d"), ("last_offer_ago", "last_offer_days_ago"),
                 ("offers_this_week", "offers_this_week"), ("opted_out", "opted_out"), ("active_hour", "active_hour")]


def _rows(customers: list[dict]) -> dict[str, list[tuple]]:
    rows = {"customers": [], "orders": [], "cart_items": [], "browsing": [], "hidden_personas": []}
    for c in customers:
        rows["customers"].append(tuple(int(c[k]) if isinstance(c[k], bool) else c[k] for k, _ in CUSTOMER_COLS))
        rows["orders"] += [(c["id"], o["d"], o["cat"], o["value"], int(o["disc"]), o["pay"], int(o["ret"])) for o in c["orders"]]
        if c["cart"]:
            rows["cart_items"] += [(c["id"], x["name"], x["price"], x["cat"], c["cart"]["hours_ago"]) for x in c["cart"]["items"]]
        rows["browsing"] += [(c["id"], b["d"], b["cat"], b["item"]) for b in c["browse"]]
        rows["hidden_personas"].append((c["id"], c["_persona"]))
    return rows


def write_sqlite(customers: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)
    with sqlite3.connect(path) as db:
        db.executescript(SCHEMA)
        for table, rows in _rows(customers).items():
            if rows:
                db.executemany(f"INSERT INTO {table} VALUES ({','.join('?' * len(rows[0]))})", rows)


def write_csv(customers: list[dict], folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    headers = {
        "customers": [col for _, col in CUSTOMER_COLS],
        "orders": ["customer_id", "days_ago", "category", "value", "used_coupon", "payment", "returned"],
        "cart_items": ["customer_id", "name", "price", "category", "hours_ago"],
        "browsing": ["customer_id", "days_ago", "category", "item"],
        "hidden_personas": ["customer_id", "persona"],
    }
    for table, rows in _rows(customers).items():
        with open(folder / f"{table}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(headers[table])
            w.writerows(rows)


def load_sqlite(path: Path, with_personas: bool = False) -> list[dict]:
    """Load customers in the in-memory format. Personas are only loaded when asked for (simulation)."""
    with sqlite3.connect(path) as db:
        db.row_factory = sqlite3.Row
        by_id = {}
        for r in db.execute("SELECT * FROM customers ORDER BY id"):
            c = {k: r[col] for k, col in CUSTOMER_COLS}
            c["opted_out"] = bool(c["opted_out"])
            c.update(orders=[], cart=None, browse=[])
            by_id[c["id"]] = c
        for r in db.execute("SELECT * FROM orders ORDER BY customer_id, days_ago"):
            by_id[r["customer_id"]]["orders"].append({"d": r["days_ago"], "cat": r["category"], "value": r["value"],
                                                      "disc": bool(r["used_coupon"]), "pay": r["payment"], "ret": bool(r["returned"])})
        for r in db.execute("SELECT * FROM cart_items"):
            c = by_id[r["customer_id"]]
            if c["cart"] is None:
                c["cart"] = {"items": [], "value": 0, "hours_ago": r["hours_ago"]}
            c["cart"]["items"].append({"name": r["name"], "price": r["price"], "cat": r["category"]})
            c["cart"]["value"] += r["price"]
        for r in db.execute("SELECT * FROM browsing"):
            by_id[r["customer_id"]]["browse"].append({"d": r["days_ago"], "cat": r["category"], "item": r["item"]})
        if with_personas:
            for r in db.execute("SELECT * FROM hidden_personas"):
                by_id[r["customer_id"]]["_persona"] = r["persona"]
    return list(by_id.values())


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate synthetic BazaarKart customers.")
    ap.add_argument("--customers", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent.parent / "data" / "generated")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")              # ₹, × and – on Windows consoles
    customers = generate(args.customers, args.seed)
    write_sqlite(customers, args.out / "peshkash.db")
    write_csv(customers, args.out)
    n_orders = sum(len(c["orders"]) for c in customers)
    print(f"Generated {len(customers):,} customers and {n_orders:,} orders into {args.out}")
    from .realism import realism_report
    for c in realism_report(customers):
        print(f"  {'OK ' if c.ok else 'CHECK'}  {c.label}: {c.shown} (expected {c.expected})")


if __name__ == "__main__":
    main()
