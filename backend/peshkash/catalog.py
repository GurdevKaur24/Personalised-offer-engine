"""The demo store: calendar, product categories, cities, names and hidden shopper personas.

Every "days ago" number in the project counts back from TODAY (day 0).
"""
from datetime import date, timedelta

TODAY = date(2026, 10, 24)          # Sat 24 Oct 2026, campaign planning day
NOW_HOUR = 10                       # campaigns are planned at 10 am
DIWALI = date(2026, 11, 8)
DAYS_TO_DIWALI = (DIWALI - TODAY).days
HISTORY_DAYS = 550                  # about 18 months of orders


def date_ago(days: int) -> date:
    return TODAY - timedelta(days=days)


def ago_of(y: int, m: int, d: int) -> int:
    return (TODAY - date(y, m, d)).days


# (from, to, multiplier, festive?)
SALES = [
    ((2025, 6, 27), (2025, 7, 6), 1.4, False),    # end-of-season sale
    ((2025, 9, 22), (2025, 10, 21), 1.7, True),   # festive sale 2025
    ((2025, 10, 14), (2025, 10, 20), 2.6, True),  # Diwali week 2025 (Diwali 20 Oct)
    ((2026, 1, 17), (2026, 1, 21), 1.5, False),   # Republic Day sale
    ((2026, 7, 10), (2026, 7, 19), 1.4, False),   # end-of-season sale
    ((2026, 10, 1), (2026, 10, 24), 1.25, True),  # pre-Diwali build-up 2026
]


def _season() -> tuple[list[float], list[bool]]:
    season, festive = [], []
    for d in range(HISTORY_DAYS + 6):
        dt = date_ago(d)
        m = 1.0
        if dt.weekday() >= 5:
            m *= 1.2                 # weekend
        if dt.day <= 5:
            m *= 1.3                 # salary days
        sale, fest = 1.0, False
        for f, t, mult, is_f in SALES:
            if ago_of(*t) <= d <= ago_of(*f):
                sale = max(sale, mult)
                fest = fest or is_f
        season.append(m * sale)
        festive.append(fest)
    return season, festive


SEASON, FESTIVE = _season()

CATS = {
    "fashion": {"name": "Fashion", "hi": "फ़ैशन", "pa": "ਫ਼ੈਸ਼ਨ", "price": 1300, "margin": .45, "ret": .22, "share": .27,
                "items": [("Phulkari dupatta", 899), ("Cotton kurta set", 1299), ("Denim jacket", 1899), ("Punjabi jutti", 999), ("Woollen shawl", 1599)]},
    "electronics": {"name": "Electronics", "hi": "इलेक्ट्रॉनिक्स", "pa": "ਇਲੈਕਟ੍ਰਾਨਿਕਸ", "price": 3200, "margin": .12, "ret": .08, "share": .12,
                    "items": [("Wireless earbuds", 1999), ("Smartwatch", 3499), ("Power bank 20000 mAh", 1299), ("Bluetooth speaker", 2499), ("5G phone", 13999)]},
    "beauty": {"name": "Beauty", "hi": "ब्यूटी", "pa": "ਬਿਊਟੀ", "price": 650, "margin": .42, "ret": .05, "share": .14,
               "items": [("Vitamin C serum", 549), ("Kajal and lipstick combo", 399), ("Bhringraj hair oil", 299), ("Perfume 100 ml", 899), ("Face wash", 249)]},
    "home": {"name": "Home & Kitchen", "hi": "घर और रसोई", "pa": "ਘਰ ਤੇ ਰਸੋਈ", "price": 1400, "margin": .32, "ret": .07, "share": .14,
             "items": [("Steel dinner set", 1499), ("Cotton bedsheet", 899), ("Pressure cooker 5 L", 1899), ("Diya and rangoli set", 499), ("LED string lights", 349)]},
    "grocery": {"name": "Grocery", "hi": "किराना", "pa": "ਕਰਿਆਨਾ", "price": 700, "margin": .18, "ret": .01, "share": .21,
                "items": [("Basmati rice 5 kg", 649), ("Dry fruits gift box", 999), ("Desi ghee 1 L", 699), ("Masala combo", 399), ("Atta 10 kg", 449)]},
    "sports": {"name": "Sports", "hi": "खेल", "pa": "ਖੇਡਾਂ", "price": 1300, "margin": .30, "ret": .06, "share": .12,
               "items": [("Cricket bat", 1499), ("Yoga mat", 699), ("Running shoes", 2199), ("Badminton racket pair", 999), ("Gym gloves", 399)]},
}
CAT_KEYS = list(CATS)
DELIVERY_COST = 40

# (city, tier, weight)
CITIES = [("Delhi", 1, 14), ("Chandigarh", 1, 8), ("Ludhiana", 2, 12), ("Amritsar", 2, 9), ("Jalandhar", 2, 7), ("Mohali", 2, 5),
          ("Patiala", 2, 6), ("Bathinda", 3, 5), ("Moga", 3, 3), ("Hoshiarpur", 3, 3), ("Pathankot", 3, 3), ("Phagwara", 3, 2),
          ("Sangrur", 3, 3), ("Firozpur", 3, 2), ("Barnala", 3, 2), ("Karnal", 3, 3), ("Panipat", 3, 3)]
FIRST_F = ["Simran", "Harpreet", "Gurleen", "Navneet", "Priya", "Ananya", "Jasleen", "Manpreet", "Ritika", "Kirandeep",
           "Pooja", "Neha", "Amrit", "Sukhmani", "Tanvi", "Ishita", "Mehak", "Komal", "Rupinder", "Sakshi"]
FIRST_M = ["Arjun", "Harjot", "Gurpreet", "Rohan", "Karan", "Jaskaran", "Aman", "Vikram", "Rajveer", "Manav",
           "Ishaan", "Sahil", "Navdeep", "Kabir", "Yuvraj", "Ankit", "Parminder", "Rahul", "Tejbir", "Deepak"]
SURNAMES = ["Singh", "Sharma", "Gill", "Sandhu", "Verma", "Arora", "Grewal", "Bansal", "Malhotra", "Sidhu",
            "Dhillon", "Mehta", "Kapoor", "Bedi", "Chopra", "Ahuja", "Khanna", "Brar", "Garg", "Saini"]
LANGS = {"en": "English", "hi": "Hindi", "pa": "Punjabi"}

# Hidden personas drive how a synthetic customer behaves and responds to offers. The engine never reads them;
# only the data generator and the response simulation do.
# base = chance of buying in the next 14 days with no offer; s* = how much each kind of offer moves them.
PERSONAS = {
    "loyal_premium":  dict(label="Loyal premium",  share=.08, per_year=14,  aov=1.8, disc=.08, browse=10,  cart_open=.25, base=.50, s_disc=.05, s_deliv=.05, s_points=.35, s_perk=.45, opt_risk=.005),
    "regular":        dict(label="Regular",        share=.19, per_year=7,   aov=1.0, disc=.25, browse=5,   cart_open=.20, base=.26, s_disc=.35, s_deliv=.30, s_points=.25, s_perk=.15, opt_risk=.01),
    "deal_seeker":    dict(label="Deal seeker",    share=.16, per_year=6,   aov=.7,  disc=.75, browse=9,   cart_open=.35, base=.12, s_disc=.90, s_deliv=.45, s_points=.10, s_perk=.05, opt_risk=.01),
    "new_explorer":   dict(label="New explorer",   share=.11, per_year=8,   aov=.9,  disc=.35, browse=7,   cart_open=.30, base=.18, s_disc=.45, s_deliv=.50, s_points=.10, s_perk=.10, opt_risk=.015),
    "at_risk":        dict(label="Drifting away",  share=.12, per_year=8,   aov=1.1, disc=.30, browse=1.2, cart_open=.08, base=.07, s_disc=.60, s_deliv=.30, s_points=.15, s_perk=.10, opt_risk=.015),
    "window_shopper": dict(label="Window shopper", share=.13, per_year=1.5, aov=.8,  disc=.40, browse=14,  cart_open=.50, base=.04, s_disc=.20, s_deliv=.35, s_points=.05, s_perk=.05, opt_risk=.02),
    "festive_only":   dict(label="Festive only",   share=.10, per_year=2,   aov=1.3, disc=.45, browse=3,   cart_open=.20, base=.16, s_disc=.55, s_deliv=.25, s_points=.05, s_perk=.10, opt_risk=.015),
    "lapsed":         dict(label="Lapsed",         share=.11, per_year=5,   aov=.9,  disc=.30, browse=.2,  cart_open=.02, base=.02, s_disc=.20, s_deliv=.05, s_points=.02, s_perk=.02, opt_risk=.05),
}
