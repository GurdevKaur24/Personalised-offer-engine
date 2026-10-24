"""The AI agent: Claude chooses and personalises one offer within the rules.

Claude only ever sees the offer types the rules allow for this customer, with their limits. Whatever it answers is
built into an offer and checked by the rule checker. If the checker says no, Claude gets one retry with the problems
listed; if that fails too (or Claude can't be reached), the rule-based offer from `engine.decide` is used instead.
"""
import json
import os
from datetime import date
from typing import Protocol

from .catalog import CATS, LANGS, NOW_HOUR, TODAY
from .checker import Check, allowed_offers, check_customer, check_offer, failed, max_pct_by_margin
from .engine import Decision, _min_order_for_margin, decide, next_send_time
from .features import SEGMENTS, why_segment
from .offers import Offer, describe, make_offer
from .rules import OFFER_TYPES, Rules

DEFAULT_MODEL = "claude-opus-5-5"
SERVER_FALLBACK_MODELS = {"claude-opus-5-5", "claude-opus-5", "claude-fable-5-1", "claude-sonnet-5-5"}
NO_VALUE_TYPES = {"double_points", "points_reminder", "early_access"}


class AgentError(RuntimeError):
    """Claude could not give a usable answer (network, refusal, cut off, bad JSON)."""


class Chooser(Protocol):
    def choose(self, system: str, messages: list[dict], schema: dict) -> tuple[dict, object]:
        """Returns (the parsed choice, the assistant content to append to the conversation)."""


SYSTEM = """You choose one offer for one customer of BazaarKart, an Indian online store, and write its message.

Goal: win extra orders at the lowest cost to the business.
- Discounts given to people who would buy anyway are wasted. For loyal customers and champions prefer free perks
  (points, early access, reminders). Use discounts mainly for customers drifting away or who mostly buy with coupons.
- The smallest value likely to work is best. A cart or points reminder with no discount is often enough.
- Choose only from the allowed offers, and stay within their limits.

Message:
- Write in the customer's language: en = English, hi = Hindi in Devanagari, pa = Punjabi in Gurmukhi.
  Use Western digits (0-9) and ₹ for rupees.
- message_line1: greet the customer by first name with one short, friendly, relevant hook (at most 90 characters).
- message_line2: the offer itself, starting with one emoji and stating the exact value, e.g. "15%" or "₹100",
  and the minimum order if there is one, e.g. "₹100 off orders above ₹999" (at most 90 characters).
  Don't mention any other amount.
- Don't write the coupon code or the expiry date; they are added automatically.
- No false urgency, no promises you can't keep, never use these words: {banned}.

reason: one plain-English sentence for the marketing team saying why this offer suits this customer, using their facts.
Set values that don't apply to the chosen offer to 0, and category to "none" unless the offer is "pct_off"."""


def schema_for(types: list[str]) -> dict:
    return {
        "type": "object",
        "properties": {
            "offer_type": {"type": "string", "enum": types},
            "category": {"type": "string", "enum": list(CATS) + ["none"]},
            "percent_off": {"type": "integer"},
            "flat_off": {"type": "integer"},
            "min_order": {"type": "integer"},
            "message_line1": {"type": "string"},
            "message_line2": {"type": "string"},
            "reason": {"type": "string"},
        },
        "required": ["offer_type", "category", "percent_off", "flat_off", "min_order", "message_line1", "message_line2", "reason"],
        "additionalProperties": False,
    }


def _limits(c: dict, t: str, r: Rules) -> str:
    """One line per allowed offer type, with the limits that apply to this customer."""
    floor = r.margin_floor
    if t == "pct_off":
        cats = [f"{CATS[k]['name']} up to {min(r.max_pct, max_pct_by_margin(CATS[k]['margin'], r))}%" for k in CATS
                if min(r.max_pct, max_pct_by_margin(CATS[k]["margin"], r)) >= 5]
        return f"pct_off: % off one category, at least 5%. Most allowed per category (margin floor {floor}%): {'; '.join(cats)}."
    if t == "win_back":
        return f"win_back: % off their next order, 5% to {min(r.max_pct, max_pct_by_margin(c['blend_margin'], r))}%."
    if t in ("flat_off", "welcome"):
        top = min(r.max_flat, r.welcome_flat) if t == "welcome" else r.max_flat
        room = c["blend_margin"] - floor / 100
        need = f"min_order must be at least {1 / room:.1f} × the amount off" if room > .01 else "not possible (margin too thin)"
        what = "a welcome amount off their next order" if t == "welcome" else "flat ₹ off above a minimum order"
        return f"{t}: {what}, ₹50 to ₹{top}; {need}."
    if t == "free_delivery":
        need = _min_order_for_margin(40, c["blend_margin"], r)
        return f"free_delivery: free delivery on the next order; min_order 0, or at least ₹{need} if their orders are smaller." if need else \
            "free_delivery: free delivery (margin too thin; avoid)."
    if t == "cart_reminder":
        return f"cart_reminder: remind them about their cart; percent_off 0 (usually best) or up to {min(r.cart_max_pct, r.max_pct, max_pct_by_margin(c['cart']['margin'], r))}%."
    return {"double_points": "double_points: 2× loyalty points on the next order (no values).",
            "points_reminder": f"points_reminder: {c['pts_exp']} points (₹{c['pts_exp']}) expire within 30 days (no values).",
            "early_access": "early_access: shop the Diwali sale 24 hours early (no values)."}[t]


def customer_brief(c: dict, types: list[str], r: Rules, suggestion: Offer | None) -> str:
    fav = ", ".join(CATS[k]["name"] for k in c["top_cats"][:3]) or "unknown"
    lines = [
        f"Customer: {c['first']}, {c['age']}, {c['city']} (tier {c['tier']} city). Language: {c['lang']} ({LANGS[c['lang']]}).",
        f"Segment: {SEGMENTS[c['seg']]['label']} ({why_segment(c)})",
        f"Orders: {c['f365']} in the last 12 months, ₹{c['m365']:,} spent; average order ₹{c['aov']:,}; "
        + (f"usually orders every {c['usual_gap']} days; last order {c['recency']} days ago." if c["total"] else "has never ordered."),
        f"Uses a coupon on {(c['disc_aff'] or 0):.0%} of orders; returns {c['return_rate']:.0%}. Favourite categories: {fav}.",
        f"Points: {c['points']:,} ({c['pts_exp']} expiring within 30 days). Visits in the last 30 days: {c['sessions30']}.",
    ]
    if c["cart"]:
        items = ", ".join(f"{x['name']} (₹{x['price']:,})" for x in c["cart"]["items"])
        lines.append(f"Open cart, left {c['cart']['hours_ago']} hours ago: {items}.")
    lines += ["", "Allowed offers:"] + [f"- {_limits(c, t, r)}" for t in types]
    if suggestion:
        lines += ["", f"The rule-based engine would send: {describe(suggestion)}. You may choose differently if it suits them better."]
    return "\n".join(lines)


def _build(c: dict, choice: dict, r: Rules, hour: int, day: int, today: date) -> tuple[Offer | None, list[Check]]:
    """Turn the AI's answer into an offer, or explain why it can't be one."""
    t = choice.get("offer_type")
    nums = {k: choice.get(k) for k in ("percent_off", "flat_off", "min_order")}
    if t not in OFFER_TYPES:
        return None, [Check("allowed", False, f"“{t}” is not an offer type.")]
    if t == "cart_reminder" and not c["cart"]:
        return None, [Check("allowed", False, "Cart reminder chosen, but the customer has no open cart.")]
    if any(not isinstance(v, int) or isinstance(v, bool) or v < 0 for v in nums.values()):
        return None, [Check("discount", False, "Offer values must be whole numbers, not negative.")]
    lines = (str(choice.get("message_line1", "")).strip(), str(choice.get("message_line2", "")).strip())
    if not all(lines):
        return None, [Check("matches", False, "Both message lines must be written.")]
    cat = choice.get("category") if choice.get("category") in CATS else None
    pct = nums["percent_off"] if t in ("pct_off", "win_back", "cart_reminder") else 0
    flat = nums["flat_off"] if t in ("flat_off", "welcome") else 0
    min_order = nums["min_order"] if t in ("flat_off", "welcome", "free_delivery") else 0
    o = make_offer(c, t, r, cat=cat if t == "pct_off" else None, pct=pct, flat=flat, min_order=min_order,
                   send_hour=hour, send_day=day, today=today, custom_lines=lines, reason=str(choice.get("reason", "")).strip())
    return o, []


def ai_decide(c: dict, r: Rules, chooser: Chooser, spent: int = 0, *, now_hour: int = NOW_HOUR, today: date = TODAY,
              only: list[str] | None = None, use_holdout: bool = True) -> Decision:
    """Claude chooses within the rules; the checker decides; the rule-based offer is the safety net."""
    cust = check_customer(c, r, cart_trigger=only == ["cart_reminder"])
    rules_based = decide(c, r, spent, now_hour=now_hour, today=today, only=only, use_holdout=use_holdout)
    if failed(cust) or rules_based.outcome == "holdout":
        return rules_based                                   # blocked or held out: the AI is never asked
    types = [t for t in allowed_offers(c, r) if only is None or t in only]
    if not types:
        return rules_based
    hour, day = next_send_time(now_hour, r)
    system = SYSTEM.format(banned=", ".join(f'"{w}"' for w in r.banned) or "none")
    messages: list[dict] = [{"role": "user", "content": customer_brief(c, types, r, rules_based.offer)}]
    attempts: list[dict] = []
    for attempt in range(2):
        try:
            choice, assistant_content = chooser.choose(system, messages, schema_for(types))
        except AgentError as e:
            attempts.append({"error": str(e)})
            break
        offer, problems = _build(c, choice, r, hour, day, today)
        checks = check_offer(c, offer, r, spent) if offer else problems
        bad = failed(checks)
        attempts.append({"choice": choice, "failed": [{"id": x.id, "detail": x.detail} for x in bad]})
        if not bad:
            return Decision("offer", offer, cust + checks, offer.reason, source="ai" if attempt == 0 else "ai_retry", attempts=attempts)
        messages += [
            {"role": "assistant", "content": assistant_content},
            {"role": "user", "content": "The rule checker refused that offer:\n" + "\n".join(f"- {x.detail}" for x in bad)
             + "\nChoose again, staying within the limits."},
        ]
    rules_based.attempts = attempts
    rules_based.source = "rules"
    return rules_based


class ClaudeChooser:
    """Asks Claude through the Anthropic SDK, with structured output so the answer always parses."""

    def __init__(self, model: str | None = None, effort: str = "low", timeout: float = 45.0, client=None):
        import anthropic                                      # only needed when the real AI is used
        import httpx2

        self._anthropic = anthropic
        self.model = model or os.environ.get("PESHKASH_MODEL") or DEFAULT_MODEL
        self.effort = effort
        # IPv4 only: networks that advertise IPv6 but can't route it add ~20 s to every request.
        self.client = client or anthropic.Anthropic(
            timeout=timeout, max_retries=1,
            http_client=anthropic.DefaultHttpxClient(transport=httpx2.HTTPTransport(local_address="0.0.0.0")))

    def choose(self, system: str, messages: list[dict], schema: dict) -> tuple[dict, object]:
        a = self._anthropic
        kwargs = dict(model=self.model, max_tokens=8000, system=system, messages=messages,
                      output_config={"effort": self.effort, "format": {"type": "json_schema", "schema": schema}})
        if self.model in SERVER_FALLBACK_MODELS:             # a declined request is re-run on a fallback model, server-side
            kwargs.update(betas=["server-side-fallback-2026-07-01"], fallbacks="default")
        try:
            resp = self.client.beta.messages.create(**kwargs)
        except a.AuthenticationError as e:
            raise AgentError("The Anthropic API key was refused.") from e
        except a.RateLimitError as e:
            raise AgentError("Claude is busy (rate limited).") from e
        except a.APIStatusError as e:
            raise AgentError(f"Claude returned an error ({e.status_code}).") from e
        except a.APIConnectionError as e:
            raise AgentError("Could not reach Claude.") from e
        if resp.stop_reason == "refusal":
            raise AgentError("Claude declined this request.")
        if resp.stop_reason == "max_tokens":
            raise AgentError("Claude's answer was cut off.")
        text = next((b.text for b in resp.content if b.type == "text"), "")
        try:
            return json.loads(text), resp.content
        except json.JSONDecodeError as e:
            raise AgentError("Claude's answer was not valid JSON.") from e
