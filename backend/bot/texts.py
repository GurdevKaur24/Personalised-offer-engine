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


# The main menu (a keyboard that stays under the chat). Each position does the same as the command in MENU_LAYOUT.
MENU_LAYOUT = [["/offer", "/myoffers"], ["/shop", "/profile"], ["/newprofile", "/language", "/help"]]

T = {
    "en": {
        "welcome": "Welcome to <b>BazaarKart Offers</b> 🛍️\nThis is a demo store: you shop as one of our sample customers, with no real orders or "
                   "payments. We only keep your chat id and the buttons you tap.\n\nHere is your shopper:",
        "profile": "👤 <b>{name}</b>\n{age} · {city}\n\n🏷️ <b>Type:</b> {seg}\n🛍️ <b>Orders:</b> {orders} in 12 months · last {last}\n"
                   "❤️ <b>Likes:</b> {likes}\n⭐ <b>Points:</b> {points}",
        "cart_line": "\n🛒 <b>In cart:</b> {items}",
        "menu": [["✨ Get an offer", "🎁 My offers"], ["🛍️ Shop", "👤 My shopper"], ["🔄 New shopper", "🌐 Language", "❓ Help"]],
        "offer_header": "🎁 <b>BazaarKart</b> · an offer for you",
        "buttons": ["🛍️ Claim offer", "Not now", "Stop offers"],
        "claim": "🎉 Done! Code <code>{code}</code> is saved to your account and applies at checkout till {d}.",
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
        "my_offers": "🎁 <b>Your offers</b>",
        "my_offers_none": "You have no active offers right now. Tap <b>✨ Get an offer</b> to ask for one.",
        "valid_till": "valid till {d}",
        "status_claimed": "✅ Claimed",
        "status_open": "⏳ Not used yet",
        "help": "<b>What you can do</b>\nUse the menu below, or type:\n/offer – ask for an offer now\n/myoffers – your offers and codes\n"
                "/shop – browse and add things to your cart\n/profile – see your shopper\n/newprofile – play a different shopper\n"
                "/language – change language\n/stop – stop all offers\n\nLeave something in your cart and see what happens 😉",
        "shop": "🛍️ <b>Shop</b> · pick a category:",
        "items": "🛍️ <b>{cat}</b>\n{lines}\n\nTap an item to add it to your cart:",
        "added": "✅ Added <b>{item}</b>\n\n🛒 <b>Your cart</b>\n{lines}\n<b>Total: ₹{total:,}</b>",
        "checkout": "✅ Checkout", "more": "🛍️ Keep shopping",
        "ordered": "✅ Order placed for ₹{total:,} (demo: no payment). Thank you!",
        "cart_empty": "Your cart is empty. Send /shop to browse.",
        "unknown": "Sorry, I only understand the buttons and commands. Send /help to see them.",
    },
    "hi": {
        "welcome": "<b>BazaarKart Offers</b> में आपका स्वागत है 🛍️\nयह एक डेमो स्टोर है: आप हमारे एक नमूना ग्राहक के रूप में ख़रीदारी करते हैं, "
                   "कोई असली ऑर्डर या भुगतान नहीं होता। हम सिर्फ़ आपकी चैट आईडी और दबाए गए बटन रखते हैं।\n\nयह है आपका ग्राहक:",
        "profile": "👤 <b>{name}</b>\n{age} · {city}\n\n🏷️ <b>प्रकार:</b> {seg}\n🛍️ <b>ऑर्डर:</b> 12 महीनों में {orders} · आख़िरी {last}\n"
                   "❤️ <b>पसंद:</b> {likes}\n⭐ <b>पॉइंट्स:</b> {points}",
        "cart_line": "\n🛒 <b>कार्ट में:</b> {items}",
        "menu": [["✨ ऑफ़र माँगें", "🎁 मेरे ऑफ़र"], ["🛍️ ख़रीदारी", "👤 मेरा ग्राहक"], ["🔄 नया ग्राहक", "🌐 भाषा", "❓ मदद"]],
        "offer_header": "🎁 <b>BazaarKart</b> · आपके लिए एक ऑफ़र",
        "buttons": ["🛍️ ऑफ़र लें", "अभी नहीं", "ऑफ़र बंद करें"],
        "claim": "🎉 हो गया! कोड <code>{code}</code> आपके खाते में सेव है और {d} तक चेकआउट पर लगेगा।",
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
        "my_offers": "🎁 <b>आपके ऑफ़र</b>",
        "my_offers_none": "अभी आपके पास कोई चालू ऑफ़र नहीं है। ऑफ़र के लिए <b>✨ ऑफ़र माँगें</b> दबाएँ।",
        "valid_till": "{d} तक मान्य",
        "status_claimed": "✅ ले लिया",
        "status_open": "⏳ अभी इस्तेमाल नहीं हुआ",
        "help": "<b>आप क्या कर सकते हैं</b>\nनीचे का मेन्यू इस्तेमाल करें, या लिखें:\n/offer – अभी ऑफ़र माँगें\n/myoffers – आपके ऑफ़र और कोड\n"
                "/shop – सामान देखें और कार्ट में डालें\n/profile – अपना ग्राहक देखें\n/newprofile – दूसरा ग्राहक बनें\n"
                "/language – भाषा बदलें\n/stop – सभी ऑफ़र बंद करें\n\nकार्ट में कुछ छोड़कर देखिए क्या होता है 😉",
        "shop": "🛍️ <b>ख़रीदारी</b> · एक श्रेणी चुनें:",
        "items": "🛍️ <b>{cat}</b>\n{lines}\n\nकार्ट में डालने के लिए किसी सामान पर टैप करें:",
        "added": "✅ <b>{item}</b> जोड़ा गया\n\n🛒 <b>आपका कार्ट</b>\n{lines}\n<b>कुल: ₹{total:,}</b>",
        "checkout": "✅ चेकआउट", "more": "🛍️ और ख़रीदें",
        "ordered": "✅ ₹{total:,} का ऑर्डर हो गया (डेमो: कोई भुगतान नहीं)। धन्यवाद!",
        "cart_empty": "आपका कार्ट ख़ाली है। सामान देखने के लिए /shop भेजें।",
        "unknown": "माफ़ कीजिए, मैं सिर्फ़ बटन और कमांड समझता हूँ। देखने के लिए /help भेजें।",
    },
    "pa": {
        "welcome": "<b>BazaarKart Offers</b> ਵਿੱਚ ਤੁਹਾਡਾ ਸੁਆਗਤ ਹੈ 🛍️\nਇਹ ਇੱਕ ਡੈਮੋ ਸਟੋਰ ਹੈ: ਤੁਸੀਂ ਸਾਡੇ ਇੱਕ ਨਮੂਨਾ ਗਾਹਕ ਵਜੋਂ ਖ਼ਰੀਦਦਾਰੀ ਕਰਦੇ ਹੋ, "
                   "ਕੋਈ ਅਸਲੀ ਆਰਡਰ ਜਾਂ ਭੁਗਤਾਨ ਨਹੀਂ ਹੁੰਦਾ। ਅਸੀਂ ਸਿਰਫ਼ ਤੁਹਾਡੀ ਚੈਟ ਆਈਡੀ ਅਤੇ ਦੱਬੇ ਬਟਨ ਰੱਖਦੇ ਹਾਂ।\n\nਇਹ ਹੈ ਤੁਹਾਡਾ ਗਾਹਕ:",
        "profile": "👤 <b>{name}</b>\n{age} · {city}\n\n🏷️ <b>ਕਿਸਮ:</b> {seg}\n🛍️ <b>ਆਰਡਰ:</b> 12 ਮਹੀਨਿਆਂ ਵਿੱਚ {orders} · ਆਖ਼ਰੀ {last}\n"
                   "❤️ <b>ਪਸੰਦ:</b> {likes}\n⭐ <b>ਪੁਆਇੰਟ:</b> {points}",
        "cart_line": "\n🛒 <b>ਕਾਰਟ ਵਿੱਚ:</b> {items}",
        "menu": [["✨ ਆਫ਼ਰ ਮੰਗੋ", "🎁 ਮੇਰੇ ਆਫ਼ਰ"], ["🛍️ ਖ਼ਰੀਦਦਾਰੀ", "👤 ਮੇਰਾ ਗਾਹਕ"], ["🔄 ਨਵਾਂ ਗਾਹਕ", "🌐 ਭਾਸ਼ਾ", "❓ ਮਦਦ"]],
        "offer_header": "🎁 <b>BazaarKart</b> · ਤੁਹਾਡੇ ਲਈ ਇੱਕ ਆਫ਼ਰ",
        "buttons": ["🛍️ ਆਫ਼ਰ ਲਓ", "ਹਾਲੇ ਨਹੀਂ", "ਆਫ਼ਰ ਬੰਦ ਕਰੋ"],
        "claim": "🎉 ਹੋ ਗਿਆ! ਕੋਡ <code>{code}</code> ਤੁਹਾਡੇ ਖਾਤੇ ਵਿੱਚ ਸੇਵ ਹੈ ਅਤੇ {d} ਤੱਕ ਚੈੱਕਆਊਟ ਤੇ ਲੱਗੇਗਾ।",
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
        "my_offers": "🎁 <b>ਤੁਹਾਡੇ ਆਫ਼ਰ</b>",
        "my_offers_none": "ਹਾਲੇ ਤੁਹਾਡੇ ਕੋਲ ਕੋਈ ਚਾਲੂ ਆਫ਼ਰ ਨਹੀਂ। ਆਫ਼ਰ ਲਈ <b>✨ ਆਫ਼ਰ ਮੰਗੋ</b> ਦਬਾਓ।",
        "valid_till": "{d} ਤੱਕ ਵੈਧ",
        "status_claimed": "✅ ਲੈ ਲਿਆ",
        "status_open": "⏳ ਹਾਲੇ ਵਰਤਿਆ ਨਹੀਂ",
        "help": "<b>ਤੁਸੀਂ ਕੀ ਕਰ ਸਕਦੇ ਹੋ</b>\nਹੇਠਾਂ ਵਾਲਾ ਮੇਨੂ ਵਰਤੋ, ਜਾਂ ਲਿਖੋ:\n/offer – ਹੁਣੇ ਆਫ਼ਰ ਮੰਗੋ\n/myoffers – ਤੁਹਾਡੇ ਆਫ਼ਰ ਅਤੇ ਕੋਡ\n"
                "/shop – ਸਾਮਾਨ ਵੇਖੋ ਅਤੇ ਕਾਰਟ ਵਿੱਚ ਪਾਓ\n/profile – ਆਪਣਾ ਗਾਹਕ ਵੇਖੋ\n/newprofile – ਹੋਰ ਗਾਹਕ ਬਣੋ\n"
                "/language – ਭਾਸ਼ਾ ਬਦਲੋ\n/stop – ਸਾਰੇ ਆਫ਼ਰ ਬੰਦ ਕਰੋ\n\nਕਾਰਟ ਵਿੱਚ ਕੁਝ ਛੱਡ ਕੇ ਵੇਖੋ ਕੀ ਹੁੰਦਾ ਹੈ 😉",
        "shop": "🛍️ <b>ਖ਼ਰੀਦਦਾਰੀ</b> · ਇੱਕ ਸ਼੍ਰੇਣੀ ਚੁਣੋ:",
        "items": "🛍️ <b>{cat}</b>\n{lines}\n\nਕਾਰਟ ਵਿੱਚ ਪਾਉਣ ਲਈ ਕਿਸੇ ਸਾਮਾਨ ਤੇ ਟੈਪ ਕਰੋ:",
        "added": "✅ <b>{item}</b> ਜੋੜਿਆ ਗਿਆ\n\n🛒 <b>ਤੁਹਾਡਾ ਕਾਰਟ</b>\n{lines}\n<b>ਕੁੱਲ: ₹{total:,}</b>",
        "checkout": "✅ ਚੈੱਕਆਊਟ", "more": "🛍️ ਹੋਰ ਖ਼ਰੀਦੋ",
        "ordered": "✅ ₹{total:,} ਦਾ ਆਰਡਰ ਹੋ ਗਿਆ (ਡੈਮੋ: ਕੋਈ ਭੁਗਤਾਨ ਨਹੀਂ)। ਧੰਨਵਾਦ!",
        "cart_empty": "ਤੁਹਾਡਾ ਕਾਰਟ ਖ਼ਾਲੀ ਹੈ। ਸਾਮਾਨ ਵੇਖਣ ਲਈ /shop ਭੇਜੋ।",
        "unknown": "ਮਾਫ਼ ਕਰਨਾ, ਮੈਂ ਸਿਰਫ਼ ਬਟਨ ਅਤੇ ਕਮਾਂਡ ਸਮਝਦਾ ਹਾਂ। ਵੇਖਣ ਲਈ /help ਭੇਜੋ।",
    },
}

# Menu button text (in any language) -> the command it stands for.
MENU_COMMANDS = {label: cmd for t in T.values() for row_l, row_c in zip(t["menu"], MENU_LAYOUT) for label, cmd in zip(row_l, row_c)}

COMMANDS = [("offer", "Ask for an offer now"), ("myoffers", "Your offers and codes"), ("shop", "Browse and add to cart"),
            ("profile", "See your shopper"), ("newprofile", "Play a different shopper"), ("language", "Change language"),
            ("stop", "Stop all offers"), ("help", "What this bot can do")]

# What people see on the bot's page before pressing Start: (description, short description) per language.
DESCRIPTIONS = {
    "en": ("BazaarKart Offers: personalised deals picked for you, in English, हिंदी or ਪੰਜਾਬੀ.\n\n"
           "Tap Start, choose your language and see what we have for you.\n\nDemo store: no real orders or payments.",
           "Personalised BazaarKart deals in English, हिंदी or ਪੰਜਾਬੀ. Demo store: no real payments."),
    "hi": ("BazaarKart Offers: आपके लिए चुनी गई ख़ास डील, अंग्रेज़ी, हिंदी या पंजाबी में।\n\n"
           "Start दबाएँ, अपनी भाषा चुनें और देखें हमारे पास आपके लिए क्या है।\n\nडेमो स्टोर: कोई असली ऑर्डर या भुगतान नहीं।",
           "आपके लिए चुनी गई BazaarKart डील, हिंदी, पंजाबी या अंग्रेज़ी में। डेमो स्टोर: कोई असली भुगतान नहीं।"),
    "pa": ("BazaarKart Offers: ਤੁਹਾਡੇ ਲਈ ਚੁਣੀਆਂ ਖ਼ਾਸ ਡੀਲਾਂ, ਅੰਗਰੇਜ਼ੀ, ਹਿੰਦੀ ਜਾਂ ਪੰਜਾਬੀ ਵਿੱਚ।\n\n"
           "Start ਦਬਾਓ, ਆਪਣੀ ਭਾਸ਼ਾ ਚੁਣੋ ਅਤੇ ਵੇਖੋ ਸਾਡੇ ਕੋਲ ਤੁਹਾਡੇ ਲਈ ਕੀ ਹੈ।\n\nਡੈਮੋ ਸਟੋਰ: ਕੋਈ ਅਸਲੀ ਆਰਡਰ ਜਾਂ ਭੁਗਤਾਨ ਨਹੀਂ।",
           "ਤੁਹਾਡੇ ਲਈ ਚੁਣੀਆਂ BazaarKart ਡੀਲਾਂ, ਪੰਜਾਬੀ, ਹਿੰਦੀ ਜਾਂ ਅੰਗਰੇਜ਼ੀ ਵਿੱਚ। ਡੈਮੋ ਸਟੋਰ: ਕੋਈ ਅਸਲੀ ਭੁਗਤਾਨ ਨਹੀਂ।"),
}
