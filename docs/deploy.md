# Keeping the bot and the marketer page running all the time (Render, free)

Render runs the bot and the marketer page in the cloud, so people can use the bot while your laptop is off.
The free plan goes to sleep after about 15 minutes with no visits to the page, so a free uptime monitor visits
`/health` every 5 minutes to keep it awake.

You need: a GitHub account, a Render account (sign in with GitHub), an UptimeRobot account, your bot token and your
Anthropic API key. About 20 minutes.

## 1. Put the code on GitHub
1. On github.com, create a **new private repository** (for example `peshkash`). Don't add a README or licence.
2. In the project folder, connect it and push (replace the address with yours):
   ```
   git remote add origin https://github.com/<your-username>/peshkash.git
   git push -u origin main
   ```
   `.env`, the databases and the generated data are git-ignored, so no token, key or chat data is uploaded.

## 2. Create the service on Render
1. On render.com, sign in with GitHub and choose **New → Blueprint**.
2. Pick the `peshkash` repository. Render reads `render.yaml` and proposes one free web service called `peshkash`.
3. Fill in the three secrets when asked:
   - `TELEGRAM_BOT_TOKEN`: the token from BotFather
   - `ANTHROPIC_API_KEY`: your Anthropic key (leave empty for rule-based offers only)
   - `PESHKASH_PAGE_PASSWORD`: a password for the marketer page (anyone with the link could otherwise change the
     bot's rules; without it the page stays locked)
4. Choose **Apply** and wait until the service shows **Live**. The logs should end with
   `Bot @BazaarKartOffers_bot is running ...`.

## 3. Stop the copy on your laptop
Telegram lets only one copy of a bot run. Stop the bot on your laptop (Ctrl+C, or close that window). If both run,
the logs say "Another copy of this bot is running".

## 4. Keep it awake with UptimeRobot
1. On uptimerobot.com, add a monitor: type **HTTP(s)**, URL `https://<your-service>.onrender.com/health`,
   interval **5 minutes**.
2. `/health` needs no password and shows no data; it only answers "ok".

## 5. Check it
- Open `https://<your-service>.onrender.com`. The browser asks for a user name and password: type anything as the
  user name and your `PESHKASH_PAGE_PASSWORD` as the password. You should see **Live bot**.
- Send `/start` to the bot in Telegram. The offer appears on the Live bot screen within 10 seconds.

## Good to know
- **Data resets on restart.** The free plan has no permanent disk, so live results, the decision log and any rule
  changes made on the page are lost when Render restarts or redeploys the service (the synthetic shoppers are
  regenerated, identically, at start). For a demo, screenshot results you want to keep, and re-apply rule changes
  after a redeploy.
- **Updates:** every `git push` to `main` redeploys automatically.
- **Costs:** Render and UptimeRobot are free on these plans; Claude is billed per offer to your Anthropic account
  (about ₹1 per offer with Opus 5.5; set `PESHKASH_MODEL=claude-haiku-5-5` on Render for a fraction of that).
- **Back to the laptop:** suspend the service on Render (Settings → Suspend), then run the bot locally again.
