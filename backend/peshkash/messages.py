"""Offer messages in English, Hindi and Punjabi (the bot always uses the customer's own language)."""
import re
from datetime import date

from .catalog import CATS

MONTHS = {
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    "hi": ["जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"],
    "pa": ["ਜਨਵਰੀ", "ਫ਼ਰਵਰੀ", "ਮਾਰਚ", "ਅਪ੍ਰੈਲ", "ਮਈ", "ਜੂਨ", "ਜੁਲਾਈ", "ਅਗਸਤ", "ਸਤੰਬਰ", "ਅਕਤੂਬਰ", "ਨਵੰਬਰ", "ਦਸੰਬਰ"],
}


def fmt_date(d: date, lang: str = "en") -> str:
    return f"{d.day} {MONTHS[lang][d.month - 1]}"


MSG = {
    "en": {
        "hi": "Hi {n} 👋",
        "hook": {"champions": "Thank you for being one of our favourite shoppers!", "loyal": "Good to see you again!",
                 "new": "Welcome to BazaarKart!", "attention": "Something special for you this Diwali season.",
                 "at_risk": "We miss you at BazaarKart!", "lost": "It's been a while! Come and see what's new.",
                 "bargain": "A deal picked just for you."},
        "cart_hook": "You left something in your cart 🛒",
        "offer": {
            "pct_off": "🎁 Get {pct}% off {cat}",
            "win_back": "💌 Here's {pct}% off your next order",
            "flat_off": "💸 Get ₹{flat} off on orders above ₹{min}",
            "welcome": "👋 ₹{flat} off your next order above ₹{min}",
            "free_delivery": "🚚 Free delivery on your next order",
            "free_delivery_min": "🚚 Free delivery on your next order above ₹{min}",
            "double_points": "⭐ Earn 2× points on your next order",
            "points_reminder": "⏳ {pts} of your points (worth ₹{pts}) expire soon. Use them before they're gone",
            "cart_reminder": "🛒 Your {item} is still waiting",
            "cart_reminder_pct": "🛒 Your {item} is still waiting, now with {pct}% off",
            "early_access": "🪔 Shop our Diwali sale 24 hours before everyone else",
        },
        "code": "Code: {code} · Valid till {d}",
        "code_only": "Code: {code}",
    },
    "hi": {
        "hi": "नमस्ते {n} 👋",
        "hook": {"champions": "हमारे सबसे ख़ास ग्राहकों में से एक होने के लिए शुक्रिया!", "loyal": "आपको फिर से देखकर अच्छा लगा!",
                 "new": "BazaarKart में आपका स्वागत है!", "attention": "इस दिवाली सीज़न आपके लिए कुछ ख़ास।",
                 "at_risk": "BazaarKart पर हमें आपकी याद आ रही है!", "lost": "काफ़ी समय हो गया! आइए, देखिए क्या नया है।",
                 "bargain": "आपके लिए चुनी गई एक ख़ास डील।"},
        "cart_hook": "आपके कार्ट में कुछ छूट गया है 🛒",
        "offer": {
            "pct_off": "🎁 {cat} पर {pct}% की छूट पाएँ",
            "win_back": "💌 आपके अगले ऑर्डर पर {pct}% की छूट",
            "flat_off": "💸 ₹{min} से ज़्यादा के ऑर्डर पर ₹{flat} की छूट",
            "welcome": "👋 ₹{min} से ज़्यादा के अगले ऑर्डर पर ₹{flat} की छूट",
            "free_delivery": "🚚 आपके अगले ऑर्डर पर मुफ़्त डिलीवरी",
            "free_delivery_min": "🚚 आपके अगले ऑर्डर पर मुफ़्त डिलीवरी (₹{min} से ज़्यादा)",
            "double_points": "⭐ अगले ऑर्डर पर 2× पॉइंट्स कमाएँ",
            "points_reminder": "⏳ आपके {pts} पॉइंट्स (₹{pts} के) जल्द ख़त्म होने वाले हैं। उससे पहले इस्तेमाल करें",
            "cart_reminder": "🛒 आपका {item} अभी भी कार्ट में है",
            "cart_reminder_pct": "🛒 आपका {item} अभी भी कार्ट में है, अब {pct}% छूट के साथ",
            "early_access": "🪔 दिवाली सेल में सबसे 24 घंटे पहले ख़रीदारी करें",
        },
        "code": "कोड: {code} · {d} तक मान्य",
        "code_only": "कोड: {code}",
    },
    "pa": {
        "hi": "ਸਤ ਸ੍ਰੀ ਅਕਾਲ {n} 👋",
        "hook": {"champions": "ਸਾਡੇ ਸਭ ਤੋਂ ਖ਼ਾਸ ਗਾਹਕਾਂ ਵਿੱਚੋਂ ਇੱਕ ਹੋਣ ਲਈ ਧੰਨਵਾਦ!", "loyal": "ਤੁਹਾਨੂੰ ਮੁੜ ਵੇਖ ਕੇ ਖ਼ੁਸ਼ੀ ਹੋਈ!",
                 "new": "BazaarKart ਵਿੱਚ ਤੁਹਾਡਾ ਸੁਆਗਤ ਹੈ!", "attention": "ਇਸ ਦੀਵਾਲੀ ਸੀਜ਼ਨ ਤੁਹਾਡੇ ਲਈ ਕੁਝ ਖ਼ਾਸ।",
                 "at_risk": "BazaarKart ਤੇ ਸਾਨੂੰ ਤੁਹਾਡੀ ਯਾਦ ਆ ਰਹੀ ਹੈ!", "lost": "ਕਾਫ਼ੀ ਸਮਾਂ ਹੋ ਗਿਆ! ਆਓ, ਵੇਖੋ ਕੀ ਨਵਾਂ ਹੈ।",
                 "bargain": "ਤੁਹਾਡੇ ਲਈ ਚੁਣੀ ਇੱਕ ਖ਼ਾਸ ਡੀਲ।"},
        "cart_hook": "ਤੁਹਾਡੇ ਕਾਰਟ ਵਿੱਚ ਕੁਝ ਰਹਿ ਗਿਆ ਹੈ 🛒",
        "offer": {
            "pct_off": "🎁 {cat} ਤੇ {pct}% ਛੋਟ ਪਾਓ",
            "win_back": "💌 ਤੁਹਾਡੇ ਅਗਲੇ ਆਰਡਰ ਤੇ {pct}% ਛੋਟ",
            "flat_off": "💸 ₹{min} ਤੋਂ ਵੱਧ ਦੇ ਆਰਡਰ ਤੇ ₹{flat} ਦੀ ਛੋਟ",
            "welcome": "👋 ₹{min} ਤੋਂ ਵੱਧ ਦੇ ਅਗਲੇ ਆਰਡਰ ਤੇ ₹{flat} ਦੀ ਛੋਟ",
            "free_delivery": "🚚 ਤੁਹਾਡੇ ਅਗਲੇ ਆਰਡਰ ਤੇ ਮੁਫ਼ਤ ਡਿਲੀਵਰੀ",
            "free_delivery_min": "🚚 ਤੁਹਾਡੇ ਅਗਲੇ ਆਰਡਰ ਤੇ ਮੁਫ਼ਤ ਡਿਲੀਵਰੀ (₹{min} ਤੋਂ ਵੱਧ)",
            "double_points": "⭐ ਅਗਲੇ ਆਰਡਰ ਤੇ 2× ਪੁਆਇੰਟ ਕਮਾਓ",
            "points_reminder": "⏳ ਤੁਹਾਡੇ {pts} ਪੁਆਇੰਟ (₹{pts} ਦੇ) ਜਲਦੀ ਖ਼ਤਮ ਹੋ ਰਹੇ ਹਨ। ਪਹਿਲਾਂ ਵਰਤ ਲਓ",
            "cart_reminder": "🛒 ਤੁਹਾਡਾ {item} ਹਾਲੇ ਵੀ ਕਾਰਟ ਵਿੱਚ ਹੈ",
            "cart_reminder_pct": "🛒 ਤੁਹਾਡਾ {item} ਹਾਲੇ ਵੀ ਕਾਰਟ ਵਿੱਚ ਹੈ, ਹੁਣ {pct}% ਛੋਟ ਨਾਲ",
            "early_access": "🪔 ਦੀਵਾਲੀ ਸੇਲ ਵਿੱਚ ਸਭ ਤੋਂ 24 ਘੰਟੇ ਪਹਿਲਾਂ ਖ਼ਰੀਦਦਾਰੀ ਕਰੋ",
        },
        "code": "ਕੋਡ: {code} · {d} ਤੱਕ ਵੈਧ",
        "code_only": "ਕੋਡ: {code}",
    },
}


def render_message(c: dict, o, lang: str, no_expiry: bool = False, extra_line: str = "",
                   custom_lines: tuple[str, str] | None = None) -> str:
    """Three lines: greeting + hook, the offer, the code and expiry. `o` is an Offer.

    `custom_lines` replaces the first two lines with ones the AI wrote; the code and expiry line is always ours.
    """
    T = MSG[lang]
    cat = (CATS[o.cat]["name"] if lang == "en" else CATS[o.cat][lang]) if o.cat else ""
    key = o.type
    if o.type == "free_delivery" and o.min_order:
        key = "free_delivery_min"
    if o.type == "cart_reminder" and o.pct:
        key = "cart_reminder_pct"
    item = c["cart"]["items"][0]["name"] if o.type == "cart_reminder" else ""
    hook = T["cart_hook"] if o.type == "cart_reminder" else T["hook"][c["seg"]]
    first_two = [" ".join(x.split()) for x in custom_lines] if custom_lines else [
        f"{T['hi'].format(n=c['first'])} {hook}",
        T["offer"][key].format(pct=o.pct, cat=cat, flat=o.flat, min=o.min_order, pts=o.pts, item=item),
    ]
    lines = first_two + [
        T["code_only"].format(code=o.code) if no_expiry else T["code"].format(code=o.code, d=fmt_date(o.expiry_date, lang)),
    ]
    if extra_line:
        lines.append(extra_line)
    return "\n".join(lines)


def script_lang(text: str) -> str:
    """Which language a message is written in, from its script."""
    if re.search("[਀-੿]", text):
        return "pa"
    if re.search("[ऀ-ॿ]", text):
        return "hi"
    return "en"
