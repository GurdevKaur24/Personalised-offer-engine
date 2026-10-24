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

## Secrets
Copy `.env.example` to `.env` and fill in your own values. `.env` is git-ignored; never commit tokens or keys.
