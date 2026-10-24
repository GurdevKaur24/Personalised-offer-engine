# Peshkash: Personalised Offer Engine

Decides which offer each customer of an e-commerce platform should get and delivers it through a Telegram bot
(Hackathon 2, Punjab Jobs AI Bootcamp, J-PAL South Asia). Full plan: `docs/requirements.md`.

Demo store: **BazaarKart**, a fictional Indian general marketplace. All customer data is synthetic.

## Stack
- **prototype/index.html**: single clickable page, opens as a file. Generates synthetic data in the browser from a fixed
  seed, runs rules, a *simulated* AI pick and the rule checker, previews Telegram messages, shows results. Tailwind and
  Chart.js from CDN.
- **backend/**: Python 3.12, pytest. The `peshkash/` package is pure standard-library Python (no web framework):
  - `catalog.py`: calendar (TODAY = Sat 24 Oct 2026, sales, salary days), categories with margins, cities, hidden personas.
  - `datagen.py`: synthetic customers (fixed seed) → `data/generated/peshkash.db` + CSVs (git-ignored).
    Personas are stored in their own table `hidden_personas` and only loaded with `with_personas=True`.
  - `features.py`: `customer_view()` turns raw data into what the engine sees (RFM, churn risk, coupon use, segment)
    and drops every `_`-prefixed (hidden) key.
  - `realism.py`: nine checks that the data behaves like real shoppers.
  - `rules.py`: `Rules` (marketing limits) with plain-English validation; saved as JSON.
  - `offers.py` + `messages.py`: build one offer (value, cost, timing, code) and its message in en/hi/pa.
  - `checker.py`: the rule checker. `check_customer` + `check_offer`; `safe_to_send` is the only gate to sending.
  - Coming next: FastAPI, the Claude agent (anthropic SDK), python-telegram-bot v21.

## Run
```
cd backend; .\.venv\Scripts\python -m peshkash.datagen     # writes data/generated/ and prints the realism checks
cd backend; .\.venv\Scripts\python -m pytest
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
3. Holdout customers, opted-out customers and customers in quiet hours never get a message.
4. Every decision is logged with its reason (sent, fixed, blocked, holdout).

## Conventions
- Synthetic data only. Bot token and API keys live in `.env` (git-ignored); `.env.example` lists the names.
- Rule checker and data generator are pure Python and must have tests.
- Small Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`); keep `main` runnable.
- UI copy is plain English for a marketing team; amounts in ₹ with Indian digit grouping.
