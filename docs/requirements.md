# Requirements: Peshkash Personalised Offer Engine

## Problem
E-commerce platforms send offers to millions of customers, but not every offer is worth sending. A discount that wins
back a customer who is about to leave is valuable; the same discount sent to someone who would have bought anyway is
lost margin. Peshkash decides **which offer each customer should get, and when**, inside limits the marketing team sets,
and delivers it through a Telegram bot.

Store used for the demo: **BazaarKart**, a fictional Indian general marketplace (fashion, electronics, beauty, home,
grocery, sports). All customer data is synthetic.

## Users
| User | What they do |
|---|---|
| Marketing manager | Sets the rules (limits, budget, who may get what), runs campaigns, reads results |
| Customer on Telegram (anyone who starts the bot) | Starts the bot, gets a synthetic shopper profile, receives offers, claims or ignores them |
| Platform owner | Watches the audit log: what the AI chose, what the rules blocked and why |

## The core idea
1. **Rules set the limits.** Written in plain English, edited with sliders and toggles, no code.
2. **The AI chooses inside the limits.** It only ever sees the offers a customer is allowed, picks one, sets the value
   and writes the message.
3. **Every AI choice is checked before it is sent.** The rule checker is the source of truth for "safe to send". If a
   choice breaks a rule, the AI gets one retry with the problems listed; after that a safe rule-based offer (or no offer)
   is used. Every decision is logged with the reason.
4. **A holdout group gets nothing**, so we can measure whether offers actually caused extra purchases.

## Data (synthetic, but behaves like real data)
- Customers: name, city and city tier, age band, signup date and channel, language (English/Hindi/Punjabi), device,
  Telegram opt-in. A hidden **persona** drives behaviour and is never shown to the engine.
- Orders: date, category, value, discount used, payment mode (COD/UPI/card), returned or not.
- Browsing sessions, cart events (added, abandoned, bought), loyalty points (balance, expiry), offers received/redeemed.
- Catalog: categories with typical prices and **margins** (needed for discount limits).

Realism targets: top 20% of customers bring 60–70% of revenue; basket values are log-normal; time between orders
follows a gamma distribution per customer; weekends, salary days (1st–5th) and Diwali show spikes; COD is more common
in smaller cities; fashion has the highest return rate; most carts are abandoned (~70%).

## Customer features and segments
Recency, frequency, spend (RFM), average order value, churn risk (days since last order vs the customer's own usual
gap), discount affinity (share of orders with a coupon), return rate, favourite categories, open cart, points expiring.

Segments a marketer understands: **Champions, Loyal, New, Needs attention, At risk, Lost, Bargain hunters**, plus the
live trigger **Cart abandoner**.

## Offer types
| Offer | Cost to the business | Best for |
|---|---|---|
| % off a category | value × expected basket | At risk, Needs attention |
| Flat ₹ off above a minimum order | flat value | Bargain hunters, New |
| Free delivery | delivery cost | Low-basket customers, smaller cities |
| 2× loyalty points | points value | Loyal, Champions |
| Points expiry reminder | none | Anyone with points expiring |
| Cart reminder (no discount, then small discount) | 0, then small | Cart abandoners |
| Early access / member perk (no discount) | none | Champions (would buy anyway) |
| Win-back | larger discount | Lost, high past value |
| Second-order welcome | small | New |

## Rules (marketing-editable)
- Max discount %, max ₹ per offer, **margin floor** (an offer may never push the order margin below X%)
- Campaign budget; stop sending when it is used up
- Max offers per customer per week; minimum days between offers; quiet hours (no messages at night)
- Exclusions: opted out, bought in the last N days, return rate above X%
- Which segments may receive which offer types (grid of toggles)
- Holdout %
- Message rules: must show the expiry date, no banned words ("guaranteed", "free money", ...), length limit,
  customer's language

## Measuring whether offers work
Treatment vs holdout: redemption rate, revenue per customer, **incremental revenue**, discount cost, ROI. Count of
offers blocked or fixed by each rule. Strategy comparison on the synthetic population: "20% to everyone" vs "rules only"
vs "AI within rules".

## Advanced (roadmap)
- Uplift groups: sure things / persuadables / lost causes / do-not-disturb
- ✅ Rule-change preview on the Rules screen (changes listed, then offers, people left out, budget, average discount,
  AI fixes and expected profit, before and after; nothing saved until Save)
- Budget-aware allocation across customers; offer fatigue; festival calendar
- Hindi/Punjabi messages; message A/B variants
- Approval queue for high-value offers
- Coupon-abuse signals

## Build order
1. ✅ Docs and a clickable single-page prototype (in-browser data, simulated AI, rule checker, Telegram preview).
2. ✅ Python data generator + realism tests.
3. ✅ Rules engine and checker + tests.
4. ✅ Claude agent (structured output, retry, fallback, audit log).
5. ✅ Telegram bot (start, profile, offers with buttons, cart flow, stop); offers come from the Claude agent.
6. ✅ The bot serves the page in live mode: rules editing, live results and the decision log from real bot events.
7. ✅ Hosting setup for Render (password-protected page, health check, deploy guide).
8. Advanced features: ✅ rule-change preview; not yet: approval queue, coupon-abuse signals.
