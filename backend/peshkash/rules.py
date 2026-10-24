"""Offer rules set by the marketing team, with plain-English checks on every value.

Rules are stored as a small JSON file the app edits. `Rules.from_dict` refuses anything out of range and says why.
"""
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .features import SEG_KEYS, SEGMENTS

OFFER_TYPES = {
    "pct_off":         {"label": "% off a category",            "icon": "🏷️"},
    "flat_off":        {"label": "Flat ₹ off above a minimum",  "icon": "💸"},
    "free_delivery":   {"label": "Free delivery",               "icon": "🚚"},
    "double_points":   {"label": "2× loyalty points",           "icon": "⭐"},
    "points_reminder": {"label": "Points expiry reminder",      "icon": "⏳"},
    "cart_reminder":   {"label": "Cart reminder",               "icon": "🛒"},
    "early_access":    {"label": "Early access to Diwali sale", "icon": "🪔"},
    "win_back":        {"label": "Win-back discount",           "icon": "💌"},
    "welcome":         {"label": "Welcome offer",               "icon": "👋"},
}
OFFER_KEYS = list(OFFER_TYPES)

DEFAULT_GRID = {
    "champions": ["double_points", "points_reminder", "cart_reminder", "early_access"],
    "loyal":     ["free_delivery", "double_points", "points_reminder", "cart_reminder", "early_access"],
    "new":       ["free_delivery", "cart_reminder", "welcome"],
    "attention": ["pct_off", "flat_off", "free_delivery", "points_reminder", "cart_reminder"],
    "at_risk":   ["pct_off", "flat_off", "free_delivery", "points_reminder", "cart_reminder"],
    "lost":      ["points_reminder", "win_back"],
    "bargain":   ["flat_off", "free_delivery", "points_reminder", "cart_reminder"],
}

# key: (lowest, highest, how a marketer would say it)
LIMITS = {
    "max_pct":          (0, 90, "Biggest % discount"),
    "max_flat":         (0, 5000, "Biggest flat ₹ discount"),
    "margin_floor":     (0, 60, "Margin floor (%)"),
    "budget":           (0, 10_000_000, "Campaign budget (₹)"),
    "max_per_week":     (0, 14, "Offers per customer per week"),
    "min_gap_days":     (0, 30, "Days between two offers"),
    "quiet_from":       (0, 23, "Quiet hours start"),
    "quiet_to":         (0, 23, "Quiet hours end"),
    "skip_recent_days": (0, 60, "Skip customers who bought in the last (days)"),
    "max_return_pct":   (0, 100, "Highest return rate allowed (%)"),
    "holdout_pct":      (0, 50, "Holdout group (%)"),
    "cart_max_pct":     (0, 50, "Biggest cart-reminder discount (%)"),
    "welcome_flat":     (0, 2000, "Welcome offer (₹)"),
    "expiry_days":      (2, 60, "Longest an offer may last (days)"),
    "max_chars":        (80, 1000, "Longest message (characters)"),
}


@dataclass
class Rules:
    max_pct: int = 20
    max_flat: int = 300
    margin_floor: int = 10
    budget: int = 150_000
    max_per_week: int = 2
    min_gap_days: int = 3
    quiet_from: int = 21          # no messages from 9 pm ...
    quiet_to: int = 9             # ... to 9 am. Equal values mean no quiet hours.
    skip_recent_days: int = 3
    max_return_pct: int = 40
    holdout_pct: int = 10
    cart_max_pct: int = 5
    welcome_flat: int = 100
    expiry_days: int = 7
    require_expiry: bool = True
    cart_own_limit: bool = True    # cart reminders skip the weekly limit and gap; one reminder per cart
    max_chars: int = 350
    banned: list[str] = field(default_factory=lambda: ["guaranteed", "free money", "last chance ever", "risk-free", "100% free"])
    grid: dict[str, list[str]] = field(default_factory=lambda: {k: list(v) for k, v in DEFAULT_GRID.items()})

    def problems(self) -> list[str]:
        out = []
        for key, (lo, hi, label) in LIMITS.items():
            v = getattr(self, key)
            if isinstance(v, bool) or not isinstance(v, int):
                out.append(f"{label} must be a whole number.")
            elif not lo <= v <= hi:
                out.append(f"{label} must be between {lo:,} and {hi:,} (it is {v:,}).")
        if not isinstance(self.require_expiry, bool):
            out.append("“Show the expiry date” must be on or off.")
        if not isinstance(self.cart_own_limit, bool):
            out.append("“Cart reminders have their own limit” must be on or off.")
        if not isinstance(self.banned, list) or not all(isinstance(w, str) and w.strip() for w in self.banned):
            out.append("Banned words must be a list of words or phrases.")
        if not isinstance(self.grid, dict):
            out.append("“Who can get which offer” is missing.")
        else:
            for seg, types in self.grid.items():
                if seg not in SEGMENTS:
                    out.append(f"“{seg}” is not a customer segment.")
                    continue
                unknown = [t for t in types if t not in OFFER_TYPES]
                if unknown:
                    out.append(f"{SEGMENTS[seg]['label']}: unknown offer type {', '.join(unknown)}.")
        return out

    @classmethod
    def from_dict(cls, data: dict) -> "Rules":
        unknown = [k for k in data if k not in cls.__dataclass_fields__]
        r = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        if isinstance(r.banned, list):
            r.banned = [w.strip().lower() for w in r.banned if isinstance(w, str)] if all(isinstance(w, str) for w in r.banned) else r.banned
        if isinstance(r.grid, dict):
            r.grid = {**{s: list(v) for s, v in DEFAULT_GRID.items()}, **r.grid}     # a missing segment keeps its default
        problems = [f"Unknown rule “{k}”." for k in unknown] + r.problems()
        if problems:
            raise RulesError(problems)
        return r

    def to_dict(self) -> dict:
        return asdict(self)


class RulesError(ValueError):
    def __init__(self, problems: list[str]):
        super().__init__(" ".join(problems))
        self.problems = problems


def load_rules(path: Path) -> Rules:
    if not path.exists():
        return Rules()
    return Rules.from_dict(json.loads(path.read_text(encoding="utf-8")))


def save_rules(rules: Rules, path: Path) -> None:
    rules = Rules.from_dict(rules.to_dict())              # never save rules that would be refused on load
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rules.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
