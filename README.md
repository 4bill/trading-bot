---
title: Trading Bot
emoji: "\U0001F4B9"
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# Trading Bot — Telegram Mini App

A Telegram bot that opens a **Mini App form** where you pick a symbol / timeframe / strategy,
then either **analyze** the market or **auto-trade** it via [ccxt](https://github.com/ccxt/ccxt).

## Stack
- `aiogram` v3 — Telegram bot framework
- `FastAPI` + `uvicorn` — serves the Mini App (HTML form) and receives submissions
- `ccxt` — exchange connectivity (Binance, Bybit, OKX, Kraken, …)
- `pandas` / `numpy` — indicators (RSI, EMA cross)

## Project layout
```
trading-bot/
├── bot/
│   └── main.py              # aiogram bot: /start -> opens Mini App
├── webapp/
│   ├── main.py              # FastAPI app
│   └── static/
│       └── index.html       # the form (Telegram Mini App)
├── core/
│   ├── analyzer.py          # RSI + EMA-cross analysis
│   └── trader.py            # ccxt order placement
├── requirements.txt
├── .env.example
└── README.md
```

## Quick start

```bash
# 1. install
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. configure
cp .env.example .env
# edit .env:
#   TELEGRAM_BOT_TOKEN=<your token from @BotFather>
#   WEBAPP_URL=<public https url to the webapp>

# 3. expose the webapp over HTTPS (required by Telegram Mini Apps)
#    in another terminal:
#    ngrok http 8080   -> copy the https URL into WEBAPP_URL

# 4. run both processes
python -m webapp.main   # terminal A
python -m bot.main      # terminal B
```

Open your bot in Telegram, hit **/start**, tap **Open trading form**,
fill it in, and submit.

## Safety
- Keep `EXCHANGE_TESTNET=true` until you're confident.
- `.env` is gitignored — never commit API keys or the bot token.
- If you ever leak a token, revoke it via `@BotFather` → `/revoke`.
