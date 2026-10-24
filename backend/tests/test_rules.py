import json

import pytest

from peshkash.rules import DEFAULT_GRID, Rules, RulesError, load_rules, save_rules


def test_default_rules_are_valid():
    assert Rules().problems() == []


def test_out_of_range_value_is_refused_in_plain_english():
    with pytest.raises(RulesError) as e:
        Rules.from_dict({"max_pct": 120})
    assert e.value.problems == ["Biggest % discount must be between 0 and 90 (it is 120)."]


@pytest.mark.parametrize("data, words", [
    ({"max_discount": 10}, "Unknown rule “max_discount”"),
    ({"budget": "lots"}, "Campaign budget (₹) must be a whole number"),
    ({"holdout_pct": True}, "Holdout group (%) must be a whole number"),
    ({"expiry_days": 1}, "Longest an offer may last (days) must be between 2 and 60"),
    ({"grid": {"vip": ["pct_off"]}}, "“vip” is not a customer segment"),
    ({"grid": {"loyal": ["free_iphone"]}}, "Loyal: unknown offer type free_iphone"),
    ({"banned": ["ok", 5]}, "Banned words must be a list"),
    ({"require_expiry": "yes"}, "“Show the expiry date” must be on or off"),
    ({"cart_own_limit": 1}, "“Cart reminders have their own limit” must be on or off"),
])
def test_bad_rules_are_explained(data, words):
    with pytest.raises(RulesError) as e:
        Rules.from_dict(data)
    assert any(words in p for p in e.value.problems), e.value.problems


def test_several_problems_are_reported_together():
    with pytest.raises(RulesError) as e:
        Rules.from_dict({"max_pct": -1, "max_flat": 99999})
    assert len(e.value.problems) == 2


def test_banned_words_are_tidied():
    assert Rules.from_dict({"banned": ["  Guaranteed ", "FREE money"]}).banned == ["guaranteed", "free money"]


def test_a_segment_missing_from_the_grid_keeps_its_default():
    r = Rules.from_dict({"grid": {"loyal": ["double_points"]}})
    assert r.grid["loyal"] == ["double_points"]
    assert r.grid["champions"] == DEFAULT_GRID["champions"]


def test_save_and_load_round_trip(tmp_path):
    r = Rules.from_dict({"max_pct": 15, "quiet_from": 22, "banned": ["hurry"]})
    save_rules(r, tmp_path / "rules.json")
    assert load_rules(tmp_path / "rules.json") == r
    assert json.loads((tmp_path / "rules.json").read_text(encoding="utf-8"))["max_pct"] == 15


def test_bad_rules_are_never_saved(tmp_path):
    r = Rules()
    r.max_pct = 500
    with pytest.raises(RulesError):
        save_rules(r, tmp_path / "rules.json")
    assert not (tmp_path / "rules.json").exists()


def test_missing_rules_file_means_defaults(tmp_path):
    assert load_rules(tmp_path / "nope.json") == Rules()
