# Peshkash: Personalised Offer Engine

Decides **which offer each customer should get, and when**, for an e-commerce platform, and delivers it through a
Telegram bot. Marketing sets the rules; an AI picks and personalises offers inside them; every AI choice is checked
against the rules before it is sent.

Built for Hackathon 2, Punjab Jobs AI Bootcamp (J-PAL South Asia). All customer data is synthetic.

See [docs/requirements.md](docs/requirements.md) for the full feature list and build order.

## Try the prototype
Double-click `prototype/index.html`. It generates 1,500 synthetic BazaarKart customers in the browser and lets you:
- explore customers and their segments,
- change the offer rules,
- run a campaign and see which offers were sent, fixed or blocked (and why),
- preview the Telegram message each customer would get,
- compare results against a holdout group and against "20% off for everyone".

Open a screen directly with `index.html#overview`, `#customers`, `#rules`, `#run`, `#telegram` or `#results`.

The AI in the prototype is simulated; the real one (Claude) comes with the backend.

## Backend (so far)
Generate the synthetic data and run the tests (Windows):
```
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m peshkash.datagen
.\.venv\Scripts\python -m pytest
```
The generator writes `backend/data/generated/peshkash.db` and one CSV per table, then prints nine realism checks
(revenue concentration, cart abandonment, festive and salary-day spikes, cash on delivery by city size, returns,
basket sizes, sign-ups who never buy).

## Telegram bot
1. In Telegram, open **@BotFather**, send `/newbot`, and pick a name and a username ending in `bot`.
2. Copy `.env.example` to `.env` (project folder) and paste the token after `TELEGRAM_BOT_TOKEN=`.
3. Run it and share the link it prints (`https://t.me/<your bot>`) with classmates:
```
cd backend
.\.venv\Scripts\python -m bot.main
```
Classmates pick English, Hindi or Punjabi, get a made-up shopper profile and offers picked for it, and can claim,
postpone or stop offers. `/shop` lets them fill a cart; leave it for 2 minutes and a cart reminder arrives (if the rules
allow). Offers asked for during quiet hours wait until morning. Every decision is logged in `backend/data/live.db`.

With `ANTHROPIC_API_KEY` in `.env`, Claude chooses and writes each offer from the offers the rules allow; the rule
checker checks every choice, sends it back once if it breaks a rule, and uses the rule-based offer if it still does.
Pick the model with `PESHKASH_MODEL` (default `claude-opus-5-5`; `claude-haiku-5-5` is faster and much cheaper), or
turn the AI off with `PESHKASH_AI=0`.

## Marketer page
While the bot runs, open **http://localhost:8010** on the same computer:
- **Live bot**: classmates, offers sent, claim and stop rates, budget used, who chose each offer (AI, AI after the
  checker refused its first choice, or rules), and the latest offers. Click one to see what Claude proposed and every
  rule check.
- **Decision log**: every decision, including the ones where nothing was sent and why.
- **Rules**: the bot's real rules. Changes save automatically and apply from the bot's next decision.
- The simulation screens (overview, customers, run offers, results) work on 1,500 made-up shoppers in the browser.

## Running it all the time
`render.yaml` deploys the bot and the marketer page to Render's free plan; see [docs/deploy.md](docs/deploy.md)
(GitHub, Render, the page password and a keep-alive monitor, step by step).

## Secrets
Copy `.env.example` to `.env` and fill in your own values. `.env` is git-ignored; never commit tokens or keys.
