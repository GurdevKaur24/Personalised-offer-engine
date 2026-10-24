# Peshkash: Personalised Offer Engine

Decides which offer each customer of an e-commerce platform should get and delivers it through a Telegram bot
(Hackathon 2, Punjab Jobs AI Bootcamp, J-PAL South Asia). Full plan: `docs/requirements.md`.

Demo store: **BazaarKart**, a fictional Indian general marketplace. All customer data is synthetic.

## Stack
- **prototype/index.html**: single clickable page, opens as a file. Generates synthetic data in the browser from a fixed
  seed, runs rules, a *simulated* AI pick and the rule checker, previews Telegram messages, shows results. Tailwind and
  Chart.js from CDN.
- **backend/** (next): Python 3.12, FastAPI, SQLite, pytest, numpy/pandas, Faker, anthropic SDK (Claude Haiku),
  python-telegram-bot v21.

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
