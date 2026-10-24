"""The bot's behaviour, separate from the network so it can be tested with a fake Telegram.

Every offer goes through peshkash.engine.decide, which only returns offers the rule checker has passed.
Queued offers are checked again just before they are sent.
"""
import html
import json
import zlib
from datetime import datetime, time, timedelta, timezone
from pathlib import Path

from peshkash.catalog import CAT_KEYS, CATS
from peshkash.checker import check_customer, failed
from peshkash.agent import ai_decide
from peshkash.engine import decide
from peshkash.offers import describe
from peshkash.rules import Rules, load_rules

from . import texts
from .store import Store

IST = timezone(timedelta(hours=5, minutes=30))


def ist_now() -> datetime:
    return datetime.now(IST)


def esc(s) -> str:
    return html.escape(str(s), quote=False)


class OfferBot:
    def __init__(self, api, store: Store, customers: list[dict], rules: Rules | Path | None = None,
                 clock=ist_now, cart_delay: timedelta = timedelta(minutes=2), chooser=None):
        self.api, self.store, self.clock, self.cart_delay = api, store, clock, cart_delay
        self.chooser = chooser                               # the AI (Claude); None means rule-based offers only
        self._rules = rules
        self.by_id = {c["id"]: c for c in customers}
        # Profiles handed to classmates: shoppers who would get an offer today, grouped by segment for variety.
        r = self.rules()
        self.pool: dict[str, list[str]] = {}
        for c in customers:
            if decide(c, r).outcome == "offer":
                self.pool.setdefault(c["seg"], []).append(c["id"])

    def rules(self) -> Rules:
        if isinstance(self._rules, Rules):
            return self._rules
        return load_rules(self._rules) if self._rules else Rules()   # re-read every time, so edits apply at once

    # ---------- helpers ----------
    def _lang(self, chat_id: int) -> str:
        u = self.store.user(chat_id)
        return (u["lang"] if u and u["lang"] else "en")

    def _t(self, chat_id: int) -> dict:
        return texts.T[self._lang(chat_id)]

    def _send(self, chat_id: int, text: str, buttons=None) -> int:
        return self.api.send_message(chat_id, text, buttons)

    def _assign(self, chat_id: int):
        taken = self.store.taken_customers()
        segs = sorted(self.pool, key=lambda s: (sum(cid in taken for cid in self.pool[s]), s))
        for s in segs:
            free = [cid for cid in self.pool[s] if cid not in taken]
            if free:
                pick = min(free, key=lambda cid: zlib.crc32(f"{chat_id}{cid}".encode()))
                self.store.assign(chat_id, pick, self.clock())
                return
        any_id = min(self.by_id, key=lambda cid: zlib.crc32(f"{chat_id}{cid}".encode()))   # every profile taken: share one
        self.store.assign(chat_id, any_id, self.clock())

    def live_view(self, chat_id: int) -> dict:
        """The synthetic shopper as the engine sees them now, with this classmate's live activity added."""
        u, now = self.store.user(chat_id), self.clock()
        c = dict(self.by_id[u["customer_id"]])
        c["lang"] = u["lang"] or c["lang"]
        c["opted_out"] = bool(u["stopped"])
        sent = self.store.sent_times(c["id"])
        if sent:
            c["last_offer_ago"] = min(c["last_offer_ago"], (now - sent[0]).days)
            c["offers_this_week"] = sum(1 for t in sent if now - t < timedelta(days=7))
        orders = self.store.live_orders(c["id"])
        if orders:
            c["recency"] = (now - datetime.fromisoformat(orders[0]["at"])).days
        cart = self.store.cart(chat_id)
        if cart or orders:                                   # once they shop live, their real cart replaces the synthetic one
            c["cart"] = None
        if cart:
            items = cart["items"]
            value = sum(x["price"] for x in items)
            c["cart"] = {"items": items, "value": value,
                         "hours_ago": int((now - datetime.fromisoformat(cart["started_at"])).total_seconds() // 3600),
                         "margin": sum(x["price"] * CATS[x["cat"]]["margin"] for x in items) / value}
        return c

    def _profile_text(self, chat_id: int) -> str:
        c, lang = self.live_view(chat_id), self._lang(chat_id)
        T = texts.T[lang]
        likes = ", ".join(CATS[k]["name"] if lang == "en" else CATS[k][lang] for k in c["top_cats"][:2]) or "–"
        out = T["profile"].format(name=esc(c["name"]), age=esc(c["age"]), city=esc(c["city"]), seg=texts.SEG[lang][c["seg"]],
                                  orders=c["f365"], last=texts.ago(c["recency"], lang), likes=esc(likes), points=f"{c['points']:,}")
        if c["cart"]:
            out += T["cart_line"].format(items=esc(", ".join(x["name"] for x in c["cart"]["items"])))
        return out

    # ---------- offers ----------
    def try_offer(self, chat_id: int, trigger: str, only: list[str] | None = None) -> int | None:
        """Decide and send (or queue) an offer. Returns the offer id, or None with an explanation sent."""
        now, r, T = self.clock(), self.rules(), self._t(chat_id)
        c = self.live_view(chat_id)
        kw = dict(now_hour=now.hour, today=now.date(), only=only, use_holdout=False)
        if self.chooser:
            if hasattr(self.api, "send_typing"):
                self.api.send_typing(chat_id)                # Claude takes a few seconds
            d = ai_decide(c, r, self.chooser, self.store.spent(), **kw)
        else:
            d = decide(c, r, self.store.spent(), **kw)
        self.store.log(chat_id, "decision", json.dumps({"trigger": trigger, "customer": c["id"], "outcome": d.outcome,
                                                        "offer": describe(d.offer) if d.offer else None, "reason": d.reason,
                                                        "failed": [x.id for x in failed(d.checks)], "source": d.source,
                                                        "ai_attempts": d.attempts}, ensure_ascii=False), now)
        if d.outcome != "offer":
            if only:                                         # a silent trigger (cart): say nothing
                return None
            ids = {x.id for x in failed(d.checks)}
            if "optout" in ids:
                self._send(chat_id, T["stopped_note"])
            elif ids & {"gap", "weekcap"}:
                self._send(chat_id, T["too_soon"].format(days=r.min_gap_days))
            elif "recent" in ids:
                self._send(chat_id, T["recent_buy"].format(days=r.skip_recent_days))
            elif "budget" in ids:
                self._send(chat_id, T["budget"])
            else:
                self._send(chat_id, T["no_offer"])
            return None
        o = d.offer
        send_at = now if (o.send_day == 0 and o.send_hour == now.hour) else \
            datetime.combine(now.date() + timedelta(days=o.send_day), time(o.send_hour), IST)
        oid = self.store.add_offer(chat_id, c["id"], o, describe(o), "queued", trigger, now, send_at, d.checks, d.source)
        if send_at <= now:
            self._deliver(oid)
        else:
            self._send(chat_id, T["queued"].format(q_from=f"{r.quiet_from}:00", q_to=f"{r.quiet_to}:00", at=f"{o.send_hour}:00"))
        return oid

    def _deliver(self, oid: int):
        row, now = self.store.offer(oid), self.clock()
        T = self._t(row["chat_id"])
        lines = [esc(x) for x in row["text"].split("\n")]
        lines[1] = f"<b>{lines[1]}</b>"
        buttons = [[(T["buttons"][0], f"claim:{oid}")], [(T["buttons"][1], f"later:{oid}"), (T["buttons"][2], f"stop:{oid}")]]
        mid = self._send(row["chat_id"], "\n".join(lines), buttons)
        self.store.mark_sent(oid, mid, now)
        self.store.log(row["chat_id"], "sent", f"{row['summary']} ({row['code']})", now)

    def tick(self):
        """Run often: sends queued offers that are due, and cart reminders for carts left alone."""
        now = self.clock()
        for row in self.store.due_offers(now):
            u = self.store.user(row["chat_id"])
            problems = failed(check_customer(self.live_view(row["chat_id"]), self.rules(), cart_trigger=row["trigger"] == "cart"))
            if u["stopped"] or problems:
                self.store.set_status(row["id"], "cancelled", now)
                self.store.log(row["chat_id"], "cancelled", problems[0].detail if problems else "Customer stopped offers.", now)
            else:
                self._deliver(row["id"])
        for (chat_id,) in self.store.carts_to_remind(now - self.cart_delay):
            self.store.mark_reminded(chat_id)                # one reminder per cart, even if the rules say no
            u = self.store.user(chat_id)
            if u and u["lang"] and not u["stopped"]:
                self.try_offer(chat_id, "cart", only=["cart_reminder"])

    # ---------- updates ----------
    def handle(self, update: dict):
        if "callback_query" in update:
            self._callback(update["callback_query"])
        elif "message" in update and update["message"].get("chat", {}).get("type") == "private":
            self._message(update["message"])

    def _start_profile(self, chat_id: int, fresh: bool):
        T = self._t(chat_id)
        self._send(chat_id, (T["welcome"] if fresh else T["new_profile"]) + "\n\n" + self._profile_text(chat_id))
        self.try_offer(chat_id, "start")

    def _message(self, msg: dict):
        chat_id, now = msg["chat"]["id"], self.clock()
        text = (msg.get("text") or "").strip()
        cmd = text.split()[0].split("@")[0].lower() if text.startswith("/") else ""
        u = self.store.user(chat_id)
        if u is None or cmd == "/start":
            self.store.add_user(chat_id, now)
            if u and u["stopped"]:
                self.store.set_stopped(chat_id, False)
                self.store.log(chat_id, "restarted", "Turned offers back on.", now)
            u = self.store.user(chat_id)
            if not u["lang"]:
                self._send(chat_id, texts.CHOOSE_LANG, texts.LANG_BUTTONS)
            else:
                self._start_profile(chat_id, fresh=True)
            return
        if not u["lang"] or cmd == "/language":
            self._send(chat_id, texts.CHOOSE_LANG, texts.LANG_BUTTONS)
            return
        T = self._t(chat_id)
        if cmd == "/help":
            self._send(chat_id, T["help"])
        elif cmd == "/profile":
            self._send(chat_id, self._profile_text(chat_id))
        elif cmd == "/newprofile":
            self._assign(chat_id)
            self.store.clear_cart(chat_id)
            self._start_profile(chat_id, fresh=False)
        elif cmd == "/offer":
            self.try_offer(chat_id, "asked")
        elif cmd == "/shop":
            self._shop_menu(chat_id)
        elif cmd == "/stop":
            self._stop(chat_id)
        else:
            self._send(chat_id, T["unknown"])

    def _stop(self, chat_id: int):
        now = self.clock()
        self.store.set_stopped(chat_id, True)
        self.store.cancel_queued(chat_id, now)
        self.store.log(chat_id, "stopped", "Customer stopped offers.", now)
        self._send(chat_id, self._t(chat_id)["stop"])

    def _shop_menu(self, chat_id: int):
        lang = self._lang(chat_id)
        names = [(CATS[k]["name"] if lang == "en" else CATS[k][lang], f"shop:{k}") for k in CAT_KEYS]
        self._send(chat_id, self._t(chat_id)["shop"], [names[i:i + 2] for i in range(0, len(names), 2)])

    def _callback(self, q: dict):
        chat_id, data, now = q["message"]["chat"]["id"], q.get("data", ""), self.clock()
        self.api.answer_callback(q["id"])
        u = self.store.user(chat_id)
        if u is None:
            return
        kind, _, arg = data.partition(":")
        if kind == "lang" and arg in texts.T:
            first_time = not u["lang"]
            self.store.set_lang(chat_id, arg)
            if not u["customer_id"]:
                self._assign(chat_id)
            if first_time:
                self._start_profile(chat_id, fresh=True)
            else:
                self._send(chat_id, self._profile_text(chat_id))
            return
        T = self._t(chat_id)
        if kind in ("claim", "later", "stop"):
            row = self.store.offer(int(arg)) if arg.isdigit() else None
            if row is None or row["chat_id"] != chat_id:
                return
            if row["message_id"]:
                self.api.remove_buttons(chat_id, row["message_id"])
            if kind == "stop":
                self.store.set_status(row["id"], "stopped", now)
                self._stop(chat_id)
                return
            if row["status"] != "sent":
                return                                       # already answered
            self.store.set_status(row["id"], "claimed" if kind == "claim" else "later", now)
            self.store.log(chat_id, kind, f"{row['summary']} ({row['code']})", now)
            exp = row["expiry"]
            self._send(chat_id, T["claim"].format(code=esc(row["code"]), d=exp) if kind == "claim" else T["later"].format(d=exp))
        elif kind == "shop" and arg in CATS:
            items = [[(f"{name} · ₹{price:,}", f"add:{arg}:{i}")] for i, (name, price) in enumerate(CATS[arg]["items"])]
            self._send(chat_id, T["items"], items)
        elif kind == "add":
            cat, _, i = arg.partition(":")
            if cat in CATS and i.isdigit() and int(i) < len(CATS[cat]["items"]):
                name, price = CATS[cat]["items"][int(i)]
                self.store.add_to_cart(chat_id, {"name": name, "price": price, "cat": cat}, now)
                cart = self.store.cart(chat_id)
                self.store.log(chat_id, "cart", f"Added {name}", now)
                self._send(chat_id, T["added"].format(item=esc(name), n=len(cart["items"]), total=sum(x["price"] for x in cart["items"])),
                           [[(T["checkout"], "checkout:"), (T["more"], "more:")]])
        elif kind == "more":
            self._shop_menu(chat_id)
        elif kind == "checkout":
            cart = self.store.cart(chat_id)
            if not cart:
                self._send(chat_id, T["cart_empty"])
                return
            self.store.add_live_order(chat_id, u["customer_id"], now, cart["items"])
            self.store.clear_cart(chat_id)
            total = sum(x["price"] for x in cart["items"])
            self.store.log(chat_id, "order", f"₹{total}", now)
            self._send(chat_id, T["ordered"].format(total=total))
