"""The AI agent, with a fake Claude: whatever the AI answers, nothing that breaks a rule gets out."""
import json
import random
from types import SimpleNamespace

import pytest

from helpers import cart, customer, order
from peshkash.agent import AgentError, ClaudeChooser, ai_decide, customer_brief, schema_for
from peshkash.catalog import CATS
from peshkash.checker import allowed_offers, check_customer, failed
from peshkash.messages import script_lang
from peshkash.rules import Rules

R = Rules()


class FakeChooser:
    """Answers from a script; records what it was asked."""

    def __init__(self, *answers):
        self.answers, self.calls = list(answers), []

    def choose(self, system, messages, schema):
        self.calls.append({"system": system, "messages": [dict(m) for m in messages], "schema": schema})
        a = self.answers.pop(0)
        if isinstance(a, Exception):
            raise a
        return a, json.dumps(a)


def choice(offer_type="pct_off", category="fashion", percent_off=15, flat_off=0, min_order=0,
           line1="Hi Simran 👋 We miss you!", line2=None, reason="Drifting away; likes Fashion."):
    if line2 is None:
        line2 = f"🎁 {percent_off}% off Fashion, just for you" if percent_off else "⭐ Something special for you"
    return {"offer_type": offer_type, "category": category, "percent_off": percent_off, "flat_off": flat_off,
            "min_order": min_order, "message_line1": line1, "message_line2": line2, "reason": reason}


def drifting(**kw):
    base = dict(seg="at_risk", orders=[order(d) for d in (120, 150, 180, 210)], last_offer_ago=99)
    base.update(kw)
    return customer(**base)


def test_a_good_ai_choice_is_sent_with_our_code_line():
    c = drifting()
    d = ai_decide(c, R, FakeChooser(choice()), use_holdout=False)
    assert d.outcome == "offer" and d.source == "ai" and not failed(d.checks)
    lines = d.offer.text.split("\n")
    assert lines[0] == "Hi Simran 👋 We miss you!" and "15% off Fashion" in lines[1]
    assert d.offer.code in lines[2] and d.offer.expiry_label in lines[2]
    assert d.reason == "Drifting away; likes Fashion."


def test_an_over_limit_choice_goes_back_to_the_ai_with_the_problems():
    c = drifting()
    fake = FakeChooser(choice(percent_off=30), choice(percent_off=20))
    d = ai_decide(c, R, fake, use_holdout=False)
    assert d.outcome == "offer" and d.source == "ai_retry" and d.offer.pct == 20
    feedback = fake.calls[1]["messages"]
    assert feedback[1]["role"] == "assistant" and feedback[2]["role"] == "user"
    assert "Discount 30% (limit 20%)" in feedback[2]["content"]
    assert d.attempts[0]["failed"][0]["id"] == "discount" and d.attempts[1]["failed"] == []


def test_two_bad_answers_fall_back_to_the_rule_based_offer():
    c = drifting()
    d = ai_decide(c, R, FakeChooser(choice(percent_off=40), choice(percent_off=35)), use_holdout=False)
    assert d.outcome == "offer" and d.source == "rules" and len(d.attempts) == 2
    assert not failed(d.checks) and d.offer.pct <= R.max_pct


@pytest.mark.parametrize("bad, check_id", [
    (choice(line2="🎁 50% off Fashion today"), "matches"),                             # promises more than it gives
    (choice(line2="🎁 A lovely discount on Fashion"), "matches"),                      # doesn't say the value
    (choice(line2="🎁 15% off Fashion, guaranteed lowest price"), "words"),
    (choice(category="electronics", line2="🎁 15% off Electronics"), "margin"),
    (choice(offer_type="double_points", percent_off=0), "allowed"),                   # not ticked for At risk
    (choice(offer_type="flat_off", category="none", percent_off=0, flat_off=100, min_order=1499,
            line2="💸 ₹100 off your next order"), "matches"),                          # hides the minimum order
])
def test_the_checker_catches_ai_mistakes(bad, check_id):
    d = ai_decide(drifting(), R, FakeChooser(bad, bad), use_holdout=False)
    assert d.source == "rules" and check_id in [x["id"] for x in d.attempts[0]["failed"]]


def test_message_in_the_wrong_language_is_refused():
    c = drifting(lang="pa")
    d = ai_decide(c, R, FakeChooser(choice(), choice(line1="ਸਤ ਸ੍ਰੀ ਅਕਾਲ Simran 👋", line2="🎁 ਫ਼ੈਸ਼ਨ ਤੇ 15% ਛੋਟ")), use_holdout=False)
    assert d.attempts[0]["failed"][0]["id"] == "language"
    assert d.source == "ai_retry" and script_lang(d.offer.text) == "pa"


@pytest.mark.parametrize("bad", [
    choice(offer_type="free_iphone"), choice(percent_off=-5),
    choice(offer_type="cart_reminder", percent_off=0), choice(line2=""),
])
def test_nonsense_answers_never_crash_and_never_get_out(bad):
    d = ai_decide(drifting(), R, FakeChooser(bad, bad), use_holdout=False)
    assert d.source == "rules" and not failed(d.checks)


def test_if_claude_cannot_answer_the_rules_still_send_something():
    d = ai_decide(drifting(), R, FakeChooser(AgentError("Could not reach Claude.")), use_holdout=False)
    assert d.outcome == "offer" and d.source == "rules" and d.attempts == [{"error": "Could not reach Claude."}]


def test_blocked_customers_never_reach_the_ai():
    fake = FakeChooser()
    d = ai_decide(drifting(opted_out=True), R, fake)
    assert d.outcome == "blocked" and fake.calls == []


def test_the_ai_only_sees_allowed_offers_and_never_the_persona():
    c = drifting(cart=cart(("Yoga mat", 699, "sports")))
    fake = FakeChooser(choice())
    ai_decide(c, R, fake, use_holdout=False)
    sent = fake.calls[0]
    allowed = allowed_offers(c, R)
    assert sent["schema"]["properties"]["offer_type"]["enum"] == allowed
    brief = sent["messages"][0]["content"]
    assert "persona" not in brief.lower() and "Yoga mat" in brief and "Electronics up to" not in brief   # 2% < 5%: not offered
    assert '"guaranteed"' in sent["system"]


def test_cart_trigger_asks_only_about_the_cart():
    c = drifting(cart=cart(("Yoga mat", 699, "sports")))
    fake = FakeChooser(choice(offer_type="cart_reminder", category="none", percent_off=0,
                              line1="Hi Simran 👋 Your yoga mat is waiting", line2="🛒 Finish your order today"))
    d = ai_decide(c, R, fake, only=["cart_reminder"], use_holdout=False, now_hour=15)
    assert fake.calls[0]["schema"]["properties"]["offer_type"]["enum"] == ["cart_reminder"]
    assert d.source == "ai" and d.offer.type == "cart_reminder"


def test_a_misbehaving_ai_never_gets_a_rule_breaking_offer_out(customers):
    """Property test: an AI that answers at random, often beyond the limits, over every shopper."""
    rng = random.Random(3)

    class RandomAI:
        def choose(self, system, messages, schema):
            t = rng.choice(schema["properties"]["offer_type"]["enum"])
            pct, flat = rng.choice([0, 5, 10, 20, 25, 40]), rng.choice([0, 50, 100, 300, 500])
            mo = rng.choice([0, 299, 999, 2999])
            words = rng.choice(["", " guaranteed", " 99%"])
            ans = {"offer_type": t, "category": rng.choice(list(CATS) + ["none"]), "percent_off": pct, "flat_off": flat,
                   "min_order": mo, "message_line1": "Hi there 👋" + words,
                   "message_line2": f"🎁 {pct}% off and ₹{flat} off above ₹{mo}", "reason": "random"}
            return ans, json.dumps(ans)

    spent, sources = 0, set()
    for c in customers[:600]:
        d = ai_decide(c, R, RandomAI(), spent)
        if d.offer:
            assert not failed(check_customer(c, R)) and not failed(d.checks)
            spent += d.offer.cost
            sources.add(d.source)
    assert spent <= R.budget and "rules" in sources and ("ai" in sources or "ai_retry" in sources)


# ---------- The real Claude client, with a fake SDK client (no network, no cost) ----------
def fake_client(stop_reason="end_turn", text='{"offer_type": "double_points"}'):
    calls = []

    def create(**kw):
        calls.append(kw)
        return SimpleNamespace(stop_reason=stop_reason, content=[SimpleNamespace(type="text", text=text)])
    return SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(create=create))), calls


def test_claude_chooser_asks_for_structured_output_with_server_fallback():
    client, calls = fake_client()
    ans, content = ClaudeChooser(model="claude-opus-5-5", client=client).choose("sys", [{"role": "user", "content": "x"}], schema_for(["double_points"]))
    assert ans == {"offer_type": "double_points"}
    kw = calls[0]
    assert kw["model"] == "claude-opus-5-5" and kw["output_config"]["format"]["type"] == "json_schema"
    assert kw["output_config"]["effort"] == "low" and kw["fallbacks"] == "default" and kw["betas"] == ["server-side-fallback-2026-07-01"]


def test_haiku_has_no_server_fallback():
    client, calls = fake_client()
    ClaudeChooser(model="claude-haiku-5-5", client=client).choose("sys", [], schema_for(["double_points"]))
    assert "fallbacks" not in calls[0] and "betas" not in calls[0]


@pytest.mark.parametrize("stop, text", [("refusal", ""), ("max_tokens", '{"offer'), ("end_turn", "not json")])
def test_claude_chooser_turns_problems_into_agent_errors(stop, text):
    client, _ = fake_client(stop, text)
    with pytest.raises(AgentError):
        ClaudeChooser(client=client).choose("sys", [], schema_for(["double_points"]))


def test_brief_reads_like_a_marketer_wrote_it():
    c = drifting(cart=cart(("Yoga mat", 699, "sports")))
    text = customer_brief(c, allowed_offers(c, R), R, None)
    assert text.startswith("Customer: Simran") and "Allowed offers:" in text and "margin floor 10%" in text
