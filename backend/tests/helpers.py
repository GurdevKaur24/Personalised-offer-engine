from peshkash.features import customer_view


def order(d, cat="fashion", value=1300, disc=False, ret=False, pay="UPI"):
    return {"d": d, "cat": cat, "value": value, "disc": disc, "pay": pay, "ret": ret}


def raw_customer(**kw):
    base = dict(
        id="C1", first="Simran", name="Simran Kaur", gender="F", age="25–34", city="Ludhiana", tier=2, lang="en",
        signup_ago=400, orders=[order(d) for d in (20, 50, 80, 110, 140, 170)], sessions30=5, last_visit=1,
        abandoned90=2, cart=None, browse=[], points=300, pts_exp=80, last_offer_ago=10, offers_this_week=0,
        opted_out=False, active_hour=19,
    )
    base.update(kw)
    return base


def customer(seg=None, **kw):
    """A customer view (what the engine sees). `seg` overrides the worked-out segment."""
    c = customer_view(raw_customer(**kw))
    if seg:
        c["seg"] = seg
    return c


def cart(*items, hours_ago=30):
    items = [{"name": n, "price": p, "cat": cat} for n, p, cat in items]
    return {"items": items, "value": sum(x["price"] for x in items), "hours_ago": hours_ago}
