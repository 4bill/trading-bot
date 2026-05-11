# Phone-only setup (no laptop needed)

Everything below is done from your phone, in the **Telegram app** and a
**browser** (Chrome / Safari). You will not install Python or type any
terminal commands.

---

## Step 0 — Revoke the leaked bot token

You pasted the bot token in this chat, so it's public now. Kill it first:

1. Open Telegram → search **@BotFather** → open it.
2. Tap the attach icon → **Command** → pick `/revoke`.
3. Pick your bot → confirm.
4. BotFather sends you a **new** token that looks like
   `123456:AAE...`. Copy it. We'll paste it in step 3.

---

## Step 1 — Get the code into your own GitHub account

You already have the repo at **4bill/trading-bot**. Good. On your phone browser:

1. Open https://github.com/4bill/trading-bot
2. Switch to the branch **`scaffold-telegram-trading-form`**
   (tap the branch dropdown, pick it).
3. Tap **Code → Merge to main** *(or)* open the branch → **"..." → Set as default branch**.
   Easiest: on the branch page, tap **"Compare & pull request" → "Create pull request" → "Merge"**.

When you're done, the `main` branch of your repo should contain all the
files (`app.py`, `bot/`, `webapp/`, `render.yaml`, etc.).

---

## Free hosting options (pick ONE)

All three are $0 and work from your phone. If one asks for a credit card, try the next.

| # | Service | Credit card? | Sleeps when idle? |
|---|---|---|---|
| A | Render (Free tier) | No (GitHub signup) | Yes, ~15 min |
| B | Koyeb (Eco / Hobby) | No | No |
| C | Hugging Face Spaces | No, ever | No (48h idle kick) |

Instructions below are for **Render (A)**. If you picked B or C, see the
"Alternatives" section at the bottom.

---

## Step 2 — Create a free Render account

[Render](https://render.com) gives free hosting + automatic HTTPS, which is
exactly what Telegram Mini Apps require.

1. Open https://render.com on your phone.
2. Sign up with **"Continue with GitHub"** — easiest.
3. Authorize Render to read your repos.

---

## Step 3 — Deploy the bot with one tap

1. Still on Render, tap **"New +" → "Blueprint"**.
2. Pick your repo **`4bill/trading-bot`**.
3. Render reads `render.yaml` and proposes a service called `trading-bot`. Tap **Apply**.
4. It will ask for secret environment variables. Fill in:

   | Key | Value |
   |---|---|
   | `TELEGRAM_BOT_TOKEN` | the **new** token from BotFather (step 0) |
   | `WEBAPP_URL` | leave blank for now, we'll fill it after first deploy |
   | `EXCHANGE_API_KEY` | leave blank |
   | `EXCHANGE_API_SECRET` | leave blank |

5. Tap **Create**. Render starts building (2–3 min). When the status goes
   green, copy the URL at the top — it looks like
   `https://trading-bot-xxxx.onrender.com`.

---

## Step 4 — Tell the bot its own URL

1. In the Render dashboard, open your service → **Environment**.
2. Edit `WEBAPP_URL` and paste the URL from step 3 (no trailing slash).
3. Tap **Save, rebuild** — Render redeploys (~1 min).

Quick test from your phone browser:
> `https://trading-bot-xxxx.onrender.com/static/index.html`

You should see the form. If you do, you're wired up.

---

## Step 5 — Use it from Telegram

1. Open Telegram → your bot → send `/start`.
2. Tap **Open trading form**.
3. Leave **Mode = Analyze**, tap **Run**.
4. You get a signal back (BUY / SELL / HOLD) with RSI + EMA values. No
   money moved, no API keys used.

If that worked → everything is live on the internet, 24/7, with HTTPS,
from your phone only.

---

## Step 6 — Enable auto-trade (only when you're ready)

1. Make a **testnet** API key:
   - Binance testnet: https://testnet.binance.vision/
   - Bybit testnet:   https://testnet.bybit.com/
2. In the Telegram form: switch **Mode → Auto-trade**.
3. Paste the testnet key + secret, keep **Use testnet** checked.
4. Start with a tiny amount like `0.001` BTC. Tap **Run**.
5. Check your exchange testnet dashboard — the order should appear.

When (and only when) you're confident, uncheck **Use testnet** and use
real keys. Trade money you can afford to lose. This is not financial advice.

---

## Free tier note

Render's free web service **sleeps after ~15 minutes of no traffic** and
takes ~30s to wake up the first time after sleeping. The bot will miss
messages while asleep. Options:

- Upgrade to Render's Starter ($7/mo) — always on.
- Or use a free uptime pinger like UptimeRobot to hit `/healthz` every 5 min.

---

## Things you might ask next

- *"Can I change the symbol list?"* → edit `webapp/static/index.html`, the `<select id="symbol">` section, commit to `main`. Render auto-redeploys.
- *"Can I add another strategy?"* → add a branch in `core/analyzer.py` and a new `<option>` in the form.
- *"How do I see logs?"* → Render dashboard → your service → **Logs** tab.
- *"How do I stop it?"* → Render dashboard → **Suspend**.


---

## Alternative B — Koyeb (no sleep, no credit card)

1. Open https://www.koyeb.com on your phone → **Sign up with GitHub**.
2. Dashboard → **Create App** → **GitHub** → pick `4bill/trading-bot`.
3. Service type: **Web service**. Builder: **Buildpack** (auto-detects Python).
4. Set the port to **8080**. Instance type: **Free / Eco**.
5. Under **Environment variables** add:
   - `TELEGRAM_BOT_TOKEN` = your BotFather token
   - `WEBAPP_URL` = leave blank for first deploy
6. Tap **Deploy**. Wait ~3 min. Copy the `https://...koyeb.app` URL.
7. Go back to **Settings → Env vars**, set `WEBAPP_URL` to that URL, **Redeploy**.

## Alternative C — Hugging Face Spaces (truly free forever)

1. Open https://huggingface.co on your phone → **Sign up** (email only, no card).
2. Top right avatar → **New Space**.
3. Name: `trading-bot`. **SDK: Docker**. **Hardware: CPU basic (free)**. **Visibility: Private** (important — keeps your token secret).
4. Create the Space. It gives you a git URL like `https://huggingface.co/spaces/<you>/trading-bot`.
5. On your phone browser, open the Space → **Files** tab → **"Contribute"** → **"Upload files"** isn't phone-friendly, so instead use the **"Git"** tab to link your GitHub repo:
   - Or simplest path: on your `trading-bot` GitHub repo page, tap **⋯ → "Mirror"** isn't a thing, so use Space's **Files → "..."  → "Import from GitHub"** and enter `4bill/trading-bot`.
6. In the Space, tap **Settings → Variables and secrets**:
   - Add secret `TELEGRAM_BOT_TOKEN` = your token
   - Add variable `WEBAPP_URL` = `https://<your-user>-trading-bot.hf.space` (shown on the Space page once it builds)
   - Add variable `PORT` = `7860`
7. Wait for the Space status to say **Running**. Test `https://<your-user>-trading-bot.hf.space/static/index.html`.

The `Dockerfile` in your repo already targets port 7860 so HF Spaces works out of the box.
