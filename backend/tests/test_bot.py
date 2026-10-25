"""The bot, driven through a fake Telegram: every message a customer would see, and every rule on the live path."""
import json
from datetime import datetime, timedelta

import pytest

from bot.app import IST, OfferBot
from bot.store import Store
from peshkash.messages import script_lang
from peshkash.rules import Rules


class FakeTelegram:
    def __init__(self):
        self.sent, self.removed, self.answered, self._id = [], [], [], 100

    def send_message(self, chat_id, text, buttons=None):
        self._id += 1
        self.sent.append({"chat": chat_id, "text": text, "buttons": buttons, "id": self._id})
        return self._id

    def answer_callback(self, callback_id, text=None):
        self.answered.append(callback_id)

    def remove_buttons(self, chat_id, message_id):
        self.removed.append(message_id)

    def last(self, chat):
        return [m for m in self.sent if m["chat"] == chat][-1]


class Clock:
    def __init__(self, at):
        self.now = at

    def __call__(self):
        return self.now


def msg(chat, text, kind="private"):
    return {"message": {"chat": {"id": chat, "type": kind}, "text": text}}


def tap(chat, data):
    return {"callback_query": {"id": f"cb{chat}{data}", "data": data, "message": {"chat": {"id": chat}}}}


@pytest.fixture
def make_bot(customers):
    def make(rules=None, at=datetime(2026, 10, 24, 14, 0, tzinfo=IST)):
        api, clock = FakeTelegram(), Clock(at)
        bot = OfferBot(api, Store(":memory:"), customers[:400], rules or Rules(), clock=clock)
        return bot, api, clock
    return make


def join(bot, api, chat, lang="en"):
    bot.handle(msg(chat, "/start"))
    bot.handle(tap(chat, f"lang:{lang}"))


def offers(bot, chat=None):
    rows = bot.store.db.execute("SELECT * FROM offers ORDER BY id").fetchall()
    return [r for r in rows if chat is None or r["chat_id"] == chat]


def offer_buttons(m):
    return [d for row in (m["buttons"] or []) for _, d in row]


def test_start_asks_for_a_language_then_sends_profile_and_offer(make_bot):
    bot, api, _ = make_bot()
    bot.handle(msg(1, "/start"))
    assert "Choose your language" in api.sent[0]["text"] and offer_buttons(api.sent[0]) == ["lang:en", "lang:hi", "lang:pa"]
    bot.handle(tap(1, "lang:pa"))
    welcome, offer_msg = api.sent[1], api.sent[2]
    assert "BazaarKart Offers" in welcome["text"] and script_lang(welcome["text"]) == "pa"
    o = offers(bot, 1)[0]
    assert o["status"] == "sent" and offer_buttons(offer_msg) == [f"claim:{o['id']}", f"later:{o['id']}", f"stop:{o['id']}"]
    assert script_lang(offer_msg["text"]) == "pa" and o["code"] in offer_msg["text"] and "<b>" in offer_msg["text"]
    assert all(c["ok"] for c in json.loads(o["checks"]))                     # it passed every rule


def test_claiming_saves_the_code_once(make_bot):
    bot, api, _ = make_bot()
    join(bot, api, 1)
    o = offers(bot, 1)[0]
    bot.handle(tap(1, f"claim:{o['id']}"))
    assert o["code"] in api.last(1)["text"] and o["expiry"] in api.last(1)["text"]
    assert offers(bot, 1)[0]["status"] == "claimed" and api.removed
    n = len(api.sent)
    bot.handle(tap(1, f"claim:{o['id']}"))
    assert len(api.sent) == n


def test_someone_else_cannot_answer_your_offer(make_bot):
    bot, api, _ = make_bot()
    join(bot, api, 1)
    join(bot, api, 2)
    o = offers(bot, 1)[0]
    bot.handle(tap(2, f"claim:{o['id']}"))
    assert offers(bot, 1)[0]["status"] == "sent"


def test_asking_again_is_refused_by_the_gap_rule(make_bot):
    bot, api, _ = make_bot()
    join(bot, api, 1)
    bot.handle(msg(1, "/offer"))
    assert "wait 3 days" in api.last(1)["text"] and len(offers(bot, 1)) == 1


def test_a_new_profile_is_a_different_shopper_and_can_get_an_offer(make_bot):
    bot, api, _ = make_bot()
    join(bot, api, 1)
    first = bot.store.user(1)["customer_id"]
    bot.handle(msg(1, "/newprofile"))
    assert bot.store.user(1)["customer_id"] != first
    assert len(offers(bot, 1)) == 2 and offers(bot, 1)[1]["customer_id"] != first


def test_stop_means_stop_until_start(make_bot):
    bot, api, clock = make_bot()
    join(bot, api, 1)
    o = offers(bot, 1)[0]
    bot.handle(tap(1, f"stop:{o['id']}"))
    assert bot.store.user(1)["stopped"] == 1 and "won't get any more offers" in api.last(1)["text"]
    bot.handle(msg(1, "/newprofile"))                                        # a new shopper is still you: still stopped
    assert "stopped offers" in api.last(1)["text"]
    clock.now += timedelta(days=5)
    bot.handle(msg(1, "/offer"))
    assert "stopped offers" in api.last(1)["text"] and len(offers(bot, 1)) == 1
    bot.handle(msg(1, "/start"))
    assert bot.store.user(1)["stopped"] == 0 and len(offers(bot, 1)) == 2


def test_offers_asked_for_at_night_wait_for_the_morning(make_bot):
    bot, api, clock = make_bot(at=datetime(2026, 10, 24, 23, 30, tzinfo=IST))
    join(bot, api, 1)
    assert "21:00" in api.last(1)["text"] and "9:00" in api.last(1)["text"]
    assert offers(bot, 1)[0]["status"] == "queued"
    clock.now = datetime(2026, 10, 25, 8, 59, tzinfo=IST)
    bot.tick()
    assert offers(bot, 1)[0]["status"] == "queued"
    clock.now = datetime(2026, 10, 25, 9, 0, tzinfo=IST)
    bot.tick()
    assert offers(bot, 1)[0]["status"] == "sent" and offer_buttons(api.last(1))[0].startswith("claim:")


def test_a_queued_offer_is_cancelled_if_they_stop_first(make_bot):
    bot, api, clock = make_bot(at=datetime(2026, 10, 24, 23, 30, tzinfo=IST))
    join(bot, api, 1)
    bot.handle(msg(1, "/stop"))
    clock.now = datetime(2026, 10, 25, 10, 0, tzinfo=IST)
    n = len(api.sent)
    bot.tick()
    assert offers(bot, 1)[0]["status"] == "cancelled" and len(api.sent) == n


def test_left_cart_gets_one_reminder(make_bot):
    bot, api, clock = make_bot()
    join(bot, api, 1)
    bot.handle(msg(1, "/shop"))
    bot.handle(tap(1, "shop:sports"))
    bot.handle(tap(1, "add:sports:1"))                                       # Yoga mat
    assert "Yoga mat" in api.last(1)["text"]
    clock.now += timedelta(minutes=1)
    bot.tick()
    assert len(offers(bot, 1)) == 1                                          # not yet
    clock.now += timedelta(minutes=2)
    bot.tick()
    reminder = offers(bot, 1)[-1]
    assert reminder["type"] == "cart_reminder" and reminder["trigger"] == "cart" and "Yoga mat" in api.last(1)["text"]
    clock.now += timedelta(minutes=10)
    bot.tick()
    assert len(offers(bot, 1)) == 2                                          # only one per cart


def test_buying_cancels_the_reminder_and_pauses_offers(make_bot):
    bot, api, clock = make_bot()
    join(bot, api, 1)
    bot.handle(tap(1, "add:grocery:0"))
    bot.handle(tap(1, "checkout:"))
    assert "Order placed" in api.last(1)["text"]
    clock.now += timedelta(minutes=5)
    bot.tick()
    assert len(offers(bot, 1)) == 1
    bot.handle(msg(1, "/newprofile"))                                        # new shopper: no recent order of their own
    assert len(offers(bot, 1)) == 2


def test_each_user_gets_a_different_shopper_of_varied_types(make_bot):
    bot, api, _ = make_bot()
    for chat in range(1, 15):
        join(bot, api, chat)
    ids = [bot.store.user(chat)["customer_id"] for chat in range(1, 15)]
    assert len(set(ids)) == len(ids)
    segs = {bot.by_id[i]["seg"] for i in ids}
    assert len(segs) >= 5


def test_budget_rule_holds_on_the_live_path(make_bot):
    bot, api, _ = make_bot(rules=Rules(budget=150))
    for chat in range(1, 12):
        join(bot, api, chat)
    assert bot.store.spent() <= 150
    assert any(o["cost"] == 0 for o in offers(bot))


def test_rules_file_changes_apply_without_restarting(make_bot, tmp_path, customers):
    path = tmp_path / "rules.json"
    path.write_text(json.dumps({"quiet_from": 0, "quiet_to": 0}), encoding="utf-8")
    api, clock = FakeTelegram(), Clock(datetime(2026, 10, 24, 23, 0, tzinfo=IST))
    bot = OfferBot(api, Store(":memory:"), customers[:400], path, clock=clock)
    join(bot, api, 1)
    assert offers(bot, 1)[0]["status"] == "sent"                             # no quiet hours: sent at 11 pm
    path.write_text(json.dumps({"quiet_from": 21, "quiet_to": 9}), encoding="utf-8")
    bot.handle(msg(1, "/newprofile"))
    assert offers(bot, 1)[1]["status"] == "queued"


def test_group_chats_are_ignored(make_bot):
    bot, api, _ = make_bot()
    bot.handle(msg(5, "/start", kind="group"))
    assert api.sent == []


def test_every_decision_is_logged(make_bot):
    bot, api, _ = make_bot()
    join(bot, api, 1)
    bot.handle(msg(1, "/offer"))
    kinds = [r["kind"] for r in bot.store.db.execute("SELECT kind FROM events")]
    assert kinds.count("decision") == 2 and "sent" in kinds


class EchoAI:
    """A fake Claude that takes the rule-based suggestion's type and writes its own two lines."""

    def __init__(self):
        self.calls = 0

    def choose(self, system, messages, schema):
        self.calls += 1
        t = schema["properties"]["offer_type"]["enum"][0]
        ans = {"offer_type": t, "category": "none", "percent_off": 0, "flat_off": 0, "min_order": 0,
               "message_line1": "Hi there 👋 A little something for you", "message_line2": "⭐ A treat from BazaarKart",
               "reason": "Fake AI reason."}
        return ans, json.dumps(ans)


def test_with_an_ai_the_bot_sends_ai_written_offers_and_records_the_source(customers):
    api, clock = FakeTelegram(), Clock(datetime(2026, 10, 24, 14, 0, tzinfo=IST))
    api.typing = []
    api.send_typing = api.typing.append
    ai = EchoAI()
    bot = OfferBot(api, Store(":memory:"), customers[:400], Rules(), clock=clock, chooser=ai)
    for chat in range(1, 8):
        join(bot, api, chat)
    rows = offers(bot)
    assert ai.calls >= 7 and api.typing
    assert {r["source"] for r in rows} <= {"ai", "ai_retry", "rules"} and any(r["source"] == "ai" for r in rows)
    for r in rows:
        assert all(c["ok"] for c in json.loads(r["checks"]))
        if r["source"] == "ai":
            assert r["text"].startswith("Hi there") and r["reason"] == "Fake AI reason."
    logged = [json.loads(e["detail"]) for e in bot.store.db.execute("SELECT detail FROM events WHERE kind='decision'")]
    assert all("source" in d and "ai_attempts" in d for d in logged)
