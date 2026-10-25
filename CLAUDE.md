# Peshkash: Personalised Offer Engine

Decides which offer each customer of an e-commerce platform should get and delivers it through a Telegram bot
(Hackathon 2, Punjab Jobs AI Bootcamp, J-PAL South Asia). Full plan: `docs/requirements.md`.

Demo store: **BazaarKart**, a fictional Indian general marketplace. All customer data is synthetic.
Bot: **@BazaarKartOffers_bot**. User-facing setup and usage: `README.md`; hosting: `docs/deploy.md`.

## Stack
- **prototype/index.html**: single clickable page, opens as a file. Generates synthetic data in the browser from a fixed
  seed, runs rules, a *simulated* AI pick and the rule checker, previews Telegram messages, shows results. Tailwind and
  Chart.js from CDN.
- **backend/**: Python 3.12, pytest, anthropic 2.3. The `peshkash/` package is plain Python (no web framework; only `agent.py` imports
  the Anthropic SDK, and only when the real AI is used):
  - `catalog.py`: calendar (TODAY = Sat 24 Oct 2026, sales, salary days), categories with margins, cities, hidden personas.
  - `datagen.py`: synthetic customers (fixed seed) → `data/generated/peshkash.db` + CSVs (git-ignored).
    Personas are stored in their own table `hidden_personas` and only loaded with `with_personas=True`.
  - `features.py`: `customer_view()` turns raw data into what the engine sees (RFM, churn risk, coupon use, segment)
    and drops every `_`-prefixed (hidden) key.
  - `realism.py`: nine checks that the data behaves like real shoppers.
  - `rules.py`: `Rules` (marketing limits) with plain-English validation; saved as JSON.
  - `offers.py` + `messages.py`: build one offer (value, cost, timing, code) and its message in en/hi/pa.
  - `checker.py`: the rule checker. `check_customer` + `check_offer`; `safe_to_send` is the only gate to sending.
    Rule `cart_own_limit`: cart reminders skip the weekly limit and gap (one reminder per cart).
  - `engine.py`: `decide()` picks the best allowed offer that passes every check (rule-based). Moves offers out of
    quiet hours. Holdout by customer id. Also the safety net for the AI.
  - `agent.py`: `ai_decide()` asks Claude (structured output; the offer-type enum is only the allowed types) to pick an
    offer and write the first two message lines; the code/expiry line is always ours. The checker checks it; on
    failure Claude gets one retry with the problems; then the rule-based offer. `Decision.source` is "ai",
    "ai_retry" or "rules"; `Decision.attempts` keeps what the AI proposed. `ClaudeChooser`: model from
    `PESHKASH_MODEL` (default claude-opus-5-5), effort low, server-side refusal fallback, IPv4-only HTTP.
  - Checker rule "matches": every % and ₹ in the message must be one the offer gives, and the value and any minimum
    order must be stated. "language" looks only at the two written lines.
- **backend/bot/**: the Telegram bot, standard library only (urllib long polling; no python-telegram-bot).
  - `app.py` (`OfferBot`): behaviour, testable with a fake Telegram. `handle(update)` + `tick()` (queued offers,
    cart reminders). Each bot user gets a synthetic shopper; their live offers, carts and orders are added on top
    (`live_view`). Queued offers are re-checked before sending. Rules are re-read from `data/rules.json` each time.
  - `store.py`: SQLite `data/live.db` (git-ignored): users (chat id only), profiles, offers, carts, live orders, events (audit log).
  - `texts.py`: everything the bot says in en/hi/pa. `telegram.py`: tiny Bot API client. `main.py`: the runner.
- **backend/web/server.py**: the marketer page, standard library `ThreadingHTTPServer` on 127.0.0.1 (default port
  8010, started by `bot.main`). Serves `prototype/index.html` and `/api/status`, `/api/rules` (GET/PUT; PUT validates
  with `Rules.from_dict` and writes `data/rules.json`, which the bot re-reads every decision), `/api/live`,
  `/api/decisions`. `Api` methods return `(status, dict)` so tests call them directly. Never sends chat ids.
- **Hosting** (`render.yaml`, guide `docs/deploy.md`): when `PORT` is set the page listens on 0.0.0.0 and every route
  except `/health` needs HTTP Basic auth with `PESHKASH_PAGE_PASSWORD` (locked with 503 if unset).
  `PESHKASH_DATA_DIR` moves `data/`. Only one copy of the bot may poll Telegram (409 Conflict otherwise).
- **prototype/index.html live mode**: when `/api/status` answers, the page adds "Live bot" and "Decision log", and the
  Rules screen loads/saves the bot's rules (camelCase in the page ↔ snake_case on the server: `toServer`/`fromServer`).
  The other screens stay a simulation on 1,500 in-browser shoppers and are labelled so.

## Run
```
cd backend; .\.venv\Scripts\python -m peshkash.datagen     # writes data/generated/ and prints the realism checks
cd backend; .\.venv\Scripts\python -m pytest
cd backend; .\.venv\Scripts\python -m bot.main   # bot + marketer page on http://localhost:8010; needs TELEGRAM_BOT_TOKEN (and ANTHROPIC_API_KEY for the AI) in ../.env
```

## Glossary
- **Persona**: hidden behaviour type used only to generate data and simulate responses. The engine never reads it.
- **Segment**: what the engine sees (Champions, Loyal, New, Needs attention, At risk, Lost, Bargain hunters), from RFM.
- **Offer**: type + value + target (category/cart) + expiry + message.
- **Rules**: marketing-set limits. **Allowed offers** = what the rules permit for one customer.
- **Holdout**: customers deliberately sent nothing, to measure uplift.
- **Incremental revenue**: revenue from offered customers minus what they would have spent anyway (holdout rate).

## Hard rules (never broken; enforced by the rule checker)
1. Nothing is sent unless the rule checker passes it. The checker is the source of truth for "safe to send".
2. The AI only sees allowed offers; its output is still re-checked (type, value, margin floor, budget, caps, message).
3. Opted-out customers never get a message, and nothing is sent during quiet hours (offers wait and are re-checked
   before sending). In campaigns, holdout customers get nothing; people trying the bot are never held out
   (`use_holdout=False` in `bot/app.py`).
4. Every decision is logged with its reason (sent, fixed, blocked, holdout).

## Conventions
- Synthetic data only. Bot token and API keys live in `.env` (git-ignored); `.env.example` lists the names.
- Rule checker and data generator are pure Python and must have tests. Tests never call the real Claude or Telegram
  (fake chooser, fake Telegram), so they are free and run offline.
- Small Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`); keep `main` runnable.
- Once hosted, every push to `main` redeploys the bot (Render) and resets its live data; until judging ends, push
  only deliberate, tested changes.
- UI copy is plain English for a marketing team; amounts in ₹ with Indian digit grouping.
