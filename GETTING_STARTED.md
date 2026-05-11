# Getting Started (zero → working bot)

No prior experience assumed. Follow in order.

---

## 0. What we just built

Three pieces that work together:

1. **Bot** (`bot/main.py`) — the thing users chat with on Telegram. It shows a button.
2. **Web form** (`webapp/static/index.html`) — what opens when you tap that button, inside Telegram.
3. **Backend** (`webapp/main.py` + `core/`) — receives the form, fetches market data, optionally places a real order.

```
You on Telegram  →  Bot  →  opens form  →  sends to backend  →  ccxt  →  Exchange
```

---

## 1. Revoke the old token (do this now)

You pasted a token in chat earlier, so it's compromised.

1. Open Telegram → message **@BotFather**
2. Send `/revoke` → choose your bot → confirm
3. BotFather gives you a **new** token — keep it private, we'll put it in `.env` in step 4.

---

## 2. Install Python 3.11+

Check:
```bash
python3 --version
```
If you don't have it, grab it from https://www.python.org/downloads/.

---

## 3. Install the project's Python packages

From inside the `trading-bot` folder:
```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

This creates an isolated "virtual environment" so installs don't pollute your system.

---

## 4. Create your `.env` file

```bash
cp .env.example .env
```

Open `.env` in any editor and fill in:

```
TELEGRAM_BOT_TOKEN=<paste the NEW token from BotFather>
WEBAPP_URL=https://example.com          # we'll replace this in step 6
EXCHANGE=binance
EXCHANGE_TESTNET=true
EXCHANGE_API_KEY=
EXCHANGE_API_SECRET=
```

Leave API key/secret empty for now — you only need them when you want to auto-trade.

---

## 5. Start the backend (the form's server)

In **Terminal A**:
```bash
source .venv/bin/activate
python -m webapp.main
```
You should see: `Uvicorn running on http://0.0.0.0:8080`.

Leave that running.

---

## 6. Give the form a public HTTPS address

Telegram Mini Apps will **only** load over `https://`, so `localhost` won't work.
The easiest free option is **ngrok**:

1. Create a free account at https://ngrok.com/download and install it.
2. In **Terminal B**:
   ```bash
   ngrok http 8080
   ```
3. Copy the `https://…ngrok-free.app` URL it prints.
4. Paste it into `.env` as `WEBAPP_URL=…` (no trailing slash).

Quick sanity check — open `https://…ngrok-free.app/static/index.html` in your browser. You should see the form.

---

## 7. Start the bot

In **Terminal C**:
```bash
source .venv/bin/activate
python -m bot.main
```

---

## 8. Try it

1. Open Telegram → find your bot → `/start`
2. Tap **Open trading form**
3. Leave **Mode = Analyze**, keep defaults, tap **Run**
4. You should see something like:
   `BTC/USDT · 1h · last 62431 — HOLD — RSI 48.3 …`

That's a full round-trip. No money was moved; no API keys were used.

---

## 9. Turn on auto-trade (only when you're ready)

1. Make a **testnet** API key on your exchange:
   - Binance: https://testnet.binance.vision/
   - Bybit:   https://testnet.bybit.com/
2. In the form, switch **Mode → Auto-trade**.
3. Paste the testnet key + secret, keep **Use testnet** checked.
4. Start with a tiny amount (e.g. `0.001` BTC). Tap **Run**.
5. Check your exchange testnet dashboard — you'll see the order.

When (and only when) you're confident, uncheck **Use testnet** and use real keys.
Do this with money you can afford to lose. This is not financial advice.

---

## Common problems

| Symptom | Fix |
|---|---|
| `TELEGRAM_BOT_TOKEN is not set` | You forgot step 4 or didn't save `.env`. |
| `WEBAPP_URL must be https://` | ngrok gives you one; paste that, not `localhost`. |
| Form button does nothing | The URL in `.env` is wrong or the webapp isn't running. |
| `Invalid Telegram initData` (401) | Your bot token in `.env` doesn't match the bot you opened the form from. |
| `Analyze failed: …` | Usually a wrong symbol format (use `BTC/USDT`, not `BTCUSDT`). |

Ping me if anything sticks.
