"""Everything the bot says, in English, Hindi and Punjabi. Offer messages themselves live in peshkash.messages."""

CHOOSE_LANG = "Choose your language · अपनी भाषा चुनें · ਆਪਣੀ ਭਾਸ਼ਾ ਚੁਣੋ"
LANG_BUTTONS = [[("English", "lang:en"), ("हिंदी", "lang:hi"), ("ਪੰਜਾਬੀ", "lang:pa")]]

SEG = {
    "en": {"champions": "Champion", "loyal": "Loyal", "new": "New", "attention": "Needs attention", "at_risk": "At risk of leaving",
           "lost": "Lost", "bargain": "Bargain hunter"},
    "hi": {"champions": "चैंपियन", "loyal": "वफ़ादार", "new": "नए ग्राहक", "attention": "ध्यान चाहिए", "at_risk": "छोड़ने के क़रीब",
           "lost": "दूर हो गए", "bargain": "डील पसंद"},
    "pa": {"champions": "ਚੈਂਪੀਅਨ", "loyal": "ਵਫ਼ਾਦਾਰ", "new": "ਨਵੇਂ ਗਾਹਕ", "attention": "ਧਿਆਨ ਚਾਹੀਦਾ", "at_risk": "ਛੱਡਣ ਦੇ ਨੇੜੇ",
           "lost": "ਦੂਰ ਹੋ ਗਏ", "bargain": "ਡੀਲ ਪਸੰਦ"},
}


def ago(days: int | None, lang: str) -> str:
    if days is None:
        return {"en": "never", "hi": "कभी नहीं", "pa": "ਕਦੇ ਨਹੀਂ"}[lang]
    if days == 0:
        return {"en": "today", "hi": "आज", "pa": "ਅੱਜ"}[lang]
    if days == 1:
        return {"en": "yesterday", "hi": "कल", "pa": "ਕੱਲ੍ਹ"}[lang]
    return {"en": f"{days} days ago", "hi": f"{days} दिन पहले", "pa": f"{days} ਦਿਨ ਪਹਿਲਾਂ"}[lang]


T = {
    "en": {
        "welcome": "Welcome to <b>BazaarKart Offers</b> 🛍️\nThis is a demo store: you shop as one of our sample customers, with no real orders or "
                   "payments. We only keep your chat id and the buttons you tap.\n\nHere is your shopper:",
        "profile": "👤 <b>{name}</b> · {age} · {city}\n🏷️ Type: {seg}\n🛍️ {orders} orders in 12 months · last order {last}\n"
                   "❤️ Likes: {likes}\n⭐ Points: {points}",
        "cart_line": "\n🛒 In cart: {items}",
        "buttons": ["🛍️ Claim offer", "Not now", "Stop offers"],
        "claim": "🎉 Done! Code <b>{code}</b> is saved to your account and applies at checkout till {d}.",
        "later": "No problem. The offer stays open till {d}.",
        "stop": "Done. You won't get any more offers. Send /start to turn them back on.",
        "stopped_note": "You have stopped offers. Send /start to turn them back on.",
        "queued": "🌙 Our rules don't send offers between {q_from} and {q_to}. Your offer will arrive at {at}.",
        "too_soon": "You got an offer recently. To avoid spamming, our rules wait {days} days between offers. "
                    "Send /newprofile to play a different shopper.",
        "recent_buy": "You just placed an order, so our rules hold offers for {days} days.",
        "budget": "This campaign's budget is used up, so there are no new offers for now.",
        "no_offer": "No offer fits our rules for this shopper right now. Send /newprofile to try another shopper.",
        "new_profile": "Here is your new shopper:",
        "help": "What you can do:\n/offer – ask for an offer now\n/shop – browse and add things to your cart\n/profile – see your shopper\n"
                "/newprofile – play a different shopper\n/stop – stop all offers\n\nLeave something in your cart and see what happens 😉",
        "shop": "🛍️ Pick a category:",
        "items": "Tap an item to add it to your cart:",
        "added": "Added <b>{item}</b>. Cart: {n} item(s), ₹{total:,}.",
        "checkout": "✅ Checkout", "more": "🛍️ Keep shopping",
        "ordered": "✅ Order placed for ₹{total:,} (demo: no payment). Thank you!",
        "cart_empty": "Your cart is empty. Send /shop to browse.",
        "unknown": "Sorry, I only understand the buttons and commands. Send /help to see them.",
    },
    "hi": {
        "welcome": "<b>BazaarKart Offers</b> में आपका स्वागत है 🛍️\nयह एक डेमो स्टोर है: आप हमारे एक नमूना ग्राहक के रूप में ख़रीदारी करते हैं, "
                   "कोई असली ऑर्डर या भुगतान नहीं होता। हम सिर्फ़ आपकी चैट आईडी और दबाए गए बटन रखते हैं।\n\nयह है आपका ग्राहक:",
        "profile": "👤 <b>{name}</b> · {age} · {city}\n🏷️ प्रकार: {seg}\n🛍️ 12 महीनों में {orders} ऑर्डर · आख़िरी ऑर्डर {last}\n"
                   "❤️ पसंद: {likes}\n⭐ पॉइंट्स: {points}",
        "cart_line": "\n🛒 कार्ट में: {items}",
        "buttons": ["🛍️ ऑफ़र लें", "अभी नहीं", "ऑफ़र बंद करें"],
        "claim": "🎉 हो गया! कोड <b>{code}</b> आपके खाते में सेव है और {d} तक चेकआउट पर लगेगा।",
        "later": "कोई बात नहीं। ऑफ़र {d} तक खुला है।",
        "stop": "ठीक है। अब आपको कोई ऑफ़र नहीं भेजा जाएगा। फिर से शुरू करने के लिए /start भेजें।",
        "stopped_note": "आपने ऑफ़र बंद किए हुए हैं। फिर से शुरू करने के लिए /start भेजें।",
        "queued": "🌙 हमारे नियमों के अनुसार {q_from} से {q_to} के बीच ऑफ़र नहीं भेजे जाते। आपका ऑफ़र {at} पर आएगा।",
        "too_soon": "आपको हाल ही में एक ऑफ़र मिला है। ज़्यादा संदेश न भेजने के लिए हमारे नियम दो ऑफ़र के बीच {days} दिन रुकते हैं। "
                    "दूसरा ग्राहक बनने के लिए /newprofile भेजें।",
        "recent_buy": "आपने अभी ऑर्डर किया है, इसलिए हमारे नियम {days} दिन तक ऑफ़र नहीं भेजते।",
        "budget": "इस अभियान का बजट ख़त्म हो गया है, इसलिए अभी कोई नया ऑफ़र नहीं है।",
        "no_offer": "अभी इस ग्राहक के लिए हमारे नियमों में कोई ऑफ़र नहीं बैठता। दूसरा ग्राहक आज़माने के लिए /newprofile भेजें।",
        "new_profile": "यह है आपका नया ग्राहक:",
        "help": "आप क्या कर सकते हैं:\n/offer – अभी ऑफ़र माँगें\n/shop – सामान देखें और कार्ट में डालें\n/profile – अपना ग्राहक देखें\n"
                "/newprofile – दूसरा ग्राहक बनें\n/stop – सभी ऑफ़र बंद करें\n\nकार्ट में कुछ छोड़कर देखिए क्या होता है 😉",
        "shop": "🛍️ एक श्रेणी चुनें:",
        "items": "कार्ट में डालने के लिए किसी सामान पर टैप करें:",
        "added": "<b>{item}</b> जोड़ा गया। कार्ट: {n} सामान, ₹{total:,}।",
        "checkout": "✅ चेकआउट", "more": "🛍️ और ख़रीदें",
        "ordered": "✅ ₹{total:,} का ऑर्डर हो गया (डेमो: कोई भुगतान नहीं)। धन्यवाद!",
        "cart_empty": "आपका कार्ट ख़ाली है। सामान देखने के लिए /shop भेजें।",
        "unknown": "माफ़ कीजिए, मैं सिर्फ़ बटन और कमांड समझता हूँ। देखने के लिए /help भेजें।",
    },
    "pa": {
        "welcome": "<b>BazaarKart Offers</b> ਵਿੱਚ ਤੁਹਾਡਾ ਸੁਆਗਤ ਹੈ 🛍️\nਇਹ ਇੱਕ ਡੈਮੋ ਸਟੋਰ ਹੈ: ਤੁਸੀਂ ਸਾਡੇ ਇੱਕ ਨਮੂਨਾ ਗਾਹਕ ਵਜੋਂ ਖ਼ਰੀਦਦਾਰੀ ਕਰਦੇ ਹੋ, "
                   "ਕੋਈ ਅਸਲੀ ਆਰਡਰ ਜਾਂ ਭੁਗਤਾਨ ਨਹੀਂ ਹੁੰਦਾ। ਅਸੀਂ ਸਿਰਫ਼ ਤੁਹਾਡੀ ਚੈਟ ਆਈਡੀ ਅਤੇ ਦੱਬੇ ਬਟਨ ਰੱਖਦੇ ਹਾਂ।\n\nਇਹ ਹੈ ਤੁਹਾਡਾ ਗਾਹਕ:",
        "profile": "👤 <b>{name}</b> · {age} · {city}\n🏷️ ਕਿਸਮ: {seg}\n🛍️ 12 ਮਹੀਨਿਆਂ ਵਿੱਚ {orders} ਆਰਡਰ · ਆਖ਼ਰੀ ਆਰਡਰ {last}\n"
                   "❤️ ਪਸੰਦ: {likes}\n⭐ ਪੁਆਇੰਟ: {points}",
        "cart_line": "\n🛒 ਕਾਰਟ ਵਿੱਚ: {items}",
        "buttons": ["🛍️ ਆਫ਼ਰ ਲਓ", "ਹਾਲੇ ਨਹੀਂ", "ਆਫ਼ਰ ਬੰਦ ਕਰੋ"],
        "claim": "🎉 ਹੋ ਗਿਆ! ਕੋਡ <b>{code}</b> ਤੁਹਾਡੇ ਖਾਤੇ ਵਿੱਚ ਸੇਵ ਹੈ ਅਤੇ {d} ਤੱਕ ਚੈੱਕਆਊਟ ਤੇ ਲੱਗੇਗਾ।",
        "later": "ਕੋਈ ਗੱਲ ਨਹੀਂ। ਆਫ਼ਰ {d} ਤੱਕ ਖੁੱਲ੍ਹਾ ਹੈ।",
        "stop": "ਠੀਕ ਹੈ। ਹੁਣ ਤੁਹਾਨੂੰ ਕੋਈ ਆਫ਼ਰ ਨਹੀਂ ਭੇਜਿਆ ਜਾਵੇਗਾ। ਮੁੜ ਸ਼ੁਰੂ ਕਰਨ ਲਈ /start ਭੇਜੋ।",
        "stopped_note": "ਤੁਸੀਂ ਆਫ਼ਰ ਬੰਦ ਕੀਤੇ ਹੋਏ ਹਨ। ਮੁੜ ਸ਼ੁਰੂ ਕਰਨ ਲਈ /start ਭੇਜੋ।",
        "queued": "🌙 ਸਾਡੇ ਨਿਯਮਾਂ ਮੁਤਾਬਕ {q_from} ਤੋਂ {q_to} ਵਿਚਕਾਰ ਆਫ਼ਰ ਨਹੀਂ ਭੇਜੇ ਜਾਂਦੇ। ਤੁਹਾਡਾ ਆਫ਼ਰ {at} ਵਜੇ ਆਵੇਗਾ।",
        "too_soon": "ਤੁਹਾਨੂੰ ਹਾਲ ਹੀ ਵਿੱਚ ਇੱਕ ਆਫ਼ਰ ਮਿਲਿਆ ਹੈ। ਬਹੁਤੇ ਸੁਨੇਹੇ ਨਾ ਭੇਜਣ ਲਈ ਸਾਡੇ ਨਿਯਮ ਦੋ ਆਫ਼ਰਾਂ ਵਿਚਕਾਰ {days} ਦਿਨ ਰੁਕਦੇ ਹਨ। "
                    "ਹੋਰ ਗਾਹਕ ਬਣਨ ਲਈ /newprofile ਭੇਜੋ।",
        "recent_buy": "ਤੁਸੀਂ ਹੁਣੇ ਆਰਡਰ ਕੀਤਾ ਹੈ, ਇਸ ਲਈ ਸਾਡੇ ਨਿਯਮ {days} ਦਿਨ ਆਫ਼ਰ ਨਹੀਂ ਭੇਜਦੇ।",
        "budget": "ਇਸ ਮੁਹਿੰਮ ਦਾ ਬਜਟ ਖ਼ਤਮ ਹੋ ਗਿਆ ਹੈ, ਇਸ ਲਈ ਹਾਲੇ ਕੋਈ ਨਵਾਂ ਆਫ਼ਰ ਨਹੀਂ।",
        "no_offer": "ਹਾਲੇ ਇਸ ਗਾਹਕ ਲਈ ਸਾਡੇ ਨਿਯਮਾਂ ਵਿੱਚ ਕੋਈ ਆਫ਼ਰ ਨਹੀਂ ਬੈਠਦਾ। ਹੋਰ ਗਾਹਕ ਅਜ਼ਮਾਉਣ ਲਈ /newprofile ਭੇਜੋ।",
        "new_profile": "ਇਹ ਹੈ ਤੁਹਾਡਾ ਨਵਾਂ ਗਾਹਕ:",
        "help": "ਤੁਸੀਂ ਕੀ ਕਰ ਸਕਦੇ ਹੋ:\n/offer – ਹੁਣੇ ਆਫ਼ਰ ਮੰਗੋ\n/shop – ਸਾਮਾਨ ਵੇਖੋ ਅਤੇ ਕਾਰਟ ਵਿੱਚ ਪਾਓ\n/profile – ਆਪਣਾ ਗਾਹਕ ਵੇਖੋ\n"
                "/newprofile – ਹੋਰ ਗਾਹਕ ਬਣੋ\n/stop – ਸਾਰੇ ਆਫ਼ਰ ਬੰਦ ਕਰੋ\n\nਕਾਰਟ ਵਿੱਚ ਕੁਝ ਛੱਡ ਕੇ ਵੇਖੋ ਕੀ ਹੁੰਦਾ ਹੈ 😉",
        "shop": "🛍️ ਇੱਕ ਸ਼੍ਰੇਣੀ ਚੁਣੋ:",
        "items": "ਕਾਰਟ ਵਿੱਚ ਪਾਉਣ ਲਈ ਕਿਸੇ ਸਾਮਾਨ ਤੇ ਟੈਪ ਕਰੋ:",
        "added": "<b>{item}</b> ਜੋੜਿਆ ਗਿਆ। ਕਾਰਟ: {n} ਸਾਮਾਨ, ₹{total:,}।",
        "checkout": "✅ ਚੈੱਕਆਊਟ", "more": "🛍️ ਹੋਰ ਖ਼ਰੀਦੋ",
        "ordered": "✅ ₹{total:,} ਦਾ ਆਰਡਰ ਹੋ ਗਿਆ (ਡੈਮੋ: ਕੋਈ ਭੁਗਤਾਨ ਨਹੀਂ)। ਧੰਨਵਾਦ!",
        "cart_empty": "ਤੁਹਾਡਾ ਕਾਰਟ ਖ਼ਾਲੀ ਹੈ। ਸਾਮਾਨ ਵੇਖਣ ਲਈ /shop ਭੇਜੋ।",
        "unknown": "ਮਾਫ਼ ਕਰਨਾ, ਮੈਂ ਸਿਰਫ਼ ਬਟਨ ਅਤੇ ਕਮਾਂਡ ਸਮਝਦਾ ਹਾਂ। ਵੇਖਣ ਲਈ /help ਭੇਜੋ।",
    },
}

COMMANDS = [("offer", "Ask for an offer now"), ("shop", "Browse and add to cart"), ("profile", "See your shopper"),
            ("newprofile", "Play a different shopper"), ("stop", "Stop all offers"), ("help", "What this bot can do")]
