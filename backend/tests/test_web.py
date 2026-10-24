"""The marketer page's API: rules the bot really uses, live results and the decision log."""
import json
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

import pytest

from bot.app import IST, OfferBot
from bot.store import Store
from test_bot import Clock, FakeTelegram, join, msg, offers, tap
from web.server import Api, serve

PAGE = Path(__file__).resolve().parents[2] / "prototype" / "index.html"


@pytest.fixture
def world(tmp_path, customers):
    """A bot and the page's API sharing one data folder, like the real thing."""
    api_t, clock = FakeTelegram(), Clock(datetime(2026, 10, 24, 14, 0, tzinfo=IST))
    bot = OfferBot(api_t, Store(tmp_path / "live.db"), customers[:400], tmp_path / "rules.json", clock=clock)
    web = Api(tmp_path, PAGE, customers[:400], {"bot": "TestBot", "ai_model": None})
    return bot, api_t, clock, web, tmp_path


def test_rules_start_as_defaults_with_their_limits(world):
    *_, web, _ = world
    code, data = web.get_rules()
    assert code == 200 and data["rules"]["max_pct"] == 20 and data["limits"]["max_pct"] == {"min": 0, "max": 90, "label": "Biggest % discount"}


def test_saved_rules_are_used_by_the_bot_at_once(world):
    bot, api_t, clock, web, _ = world
    clock.now = datetime(2026, 10, 24, 23, 0, tzinfo=IST)
    rules = web.get_rules()[1]["rules"]
    code, data = web.put_rules({**rules, "quiet_from": 0, "quiet_to": 0})            # no quiet hours
    assert code == 200 and "bot uses these rules" in data["message"]
    join(bot, api_t, 1)
    assert offers(bot, 1)[0]["status"] == "sent"                                       # sent at 11 pm


def test_bad_rules_are_refused_and_nothing_changes(world):
    *_, web, tmp_path = world
    code, data = web.put_rules({"max_pct": 120, "budget": -5})
    assert code == 400 and len(data["problems"]) == 2 and "Biggest % discount" in data["problems"][0]
    assert not (tmp_path / "rules.json").exists()
    assert web.put_rules(["not", "rules"])[0] == 400


def test_live_results_count_what_classmates_did(world):
    bot, api_t, _, web, _ = world
    for chat in (1, 2, 3):
        join(bot, api_t, chat)
    o1, o2 = offers(bot, 1)[0], offers(bot, 2)[0]
    bot.handle(tap(1, f"claim:{o1['id']}"))
    bot.handle(tap(2, f"stop:{o2['id']}"))
    code, live = web.live()
    assert code == 200 and live["classmates"] == 3 and live["stopped_users"] == 1
    assert (live["delivered"], live["claimed"], live["stopped"], live["no_answer"]) == (3, 1, 1, 1)
    assert live["claim_rate"] == pytest.approx(1 / 3) and live["by_source"] == {"rules": 3}
    first = live["recent"][-1]
    assert first["shopper"]["name"] and first["shopper"]["seg_label"] and first["checks"] and first["status"] == "claimed"


def test_classmates_chat_ids_never_reach_the_page(world):
    bot, api_t, _, web, _ = world
    join(bot, api_t, 987654321)
    page_data = json.dumps([web.live()[1], web.decisions()[1]])
    assert "987654321" not in page_data and "chat_id" not in page_data


def test_decision_log_includes_offers_not_sent_and_why(world):
    bot, api_t, _, web, _ = world
    join(bot, api_t, 1)
    bot.handle(msg(1, "/offer"))                                                       # too soon: refused
    log = web.decisions()[1]["decisions"]
    assert [d["outcome"] for d in log] == ["blocked", "offer"]                         # newest first
    refused = log[0]
    assert any(f["id"] == "gap" and "needs 3 days" in f["detail"] for f in refused["failed"])
    assert log[1]["offer_id"] == offers(bot, 1)[0]["id"]


def test_no_bot_activity_yet_still_answers(tmp_path, customers):
    web = Api(tmp_path, PAGE, customers[:10])
    assert web.live()[1]["recent"] == [] and web.decisions()[1]["decisions"] == []


def test_the_real_server_serves_the_page_and_the_api(world):
    *_, web, _ = world
    server = serve(web, port=0)
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        page = urllib.request.urlopen(base + "/").read().decode()
        assert "Peshkash" in page
        assert json.loads(urllib.request.urlopen(base + "/api/status").read())["bot"] == "TestBot"
        rules = json.loads(urllib.request.urlopen(base + "/api/rules").read())["rules"]
        req = urllib.request.Request(base + "/api/rules", data=json.dumps({**rules, "max_pct": 15}).encode(), method="PUT",
                                     headers={"Content-Type": "application/json"})
        assert json.loads(urllib.request.urlopen(req).read())["rules"]["max_pct"] == 15
        bad = urllib.request.Request(base + "/api/rules", data=b'{"max_pct": 999}', method="PUT")
        with pytest.raises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(bad)
        assert e.value.code == 400 and "Biggest % discount" in json.loads(e.value.read())["problems"][0]
    finally:
        server.shutdown()
