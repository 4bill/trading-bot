# 🪂 Airdrop Manager

Lightweight tracker for 15+ crypto airdrop projects across multiple wallets,
designed to run 24/7 on a phone via Termux.

Two interfaces, same data:

1. **Telegram bot** — primary interface for daily monitoring on mobile.
   Tap inline buttons to mark tasks done, get summaries on demand, quick-add via slash commands.
2. **Web dashboard** at `:8090` — convenient for bulk setup
   (adding the 15+ projects + tasks once via forms is faster than typing on a phone).

Plus: auto Telegram reminders twice a day so nothing slips through.

## ✨ Features

- **Telegram bot** with `/today`, `/summary`, `/pending`, `/projects`, inline-button done/undo, quick `/addproject` and `/addtask`
- **Project tracker** with categories (Testnet / Bridge-Swap / Daily Claim / Other), chain, priority and notes
- **Multi-wallet** support (only public addresses + labels — *never* private keys)
- **Tasks** with `daily` / `weekly` / `once` cadence
- **One-tap done/undo** plus an audit log of every completion
- **Auto daily reset** at 00:05 (configurable) so daily tasks come back tomorrow
- **Telegram reminders** at 08:00 and 20:00 (configurable) with a category breakdown
- Pure FastAPI + SQLite + python-telegram-bot — no build step, runs on Termux / any cheap VPS

## 🚫 What this is NOT

This tool **does not** automate Discord chatting, message sending, or any
self-bot behaviour. Self-botting violates Discord ToS and many airdrop projects
disqualify wallets caught chat-farming. Use this dashboard to stay organised and
do the work intentionally.

On-chain automation (auto-swap, auto-bridge) is intentionally **not** part of v0.1
either — those touch private keys and need their own design pass. Track them as
manual tasks for now.

## 🚀 Quick start

```bash
cd airdrop-manager
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # then edit values
python app.py
```

Open http://localhost:8090 — you should see the dashboard. Add a project, add a
few tasks. Then DM your bot on Telegram and send `/today` to see them there too.

## 🤖 Telegram bot commands

Once `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are set, DM the bot:

| Command | What it does |
|---------|-------------|
| `/today` | Pending tasks today, grouped by project, with inline ⬜→✅ buttons |
| `/summary` | Today's progress (same content as the daily reminder) |
| `/pending` | Flat list of all pending tasks |
| `/projects` | Browse projects (tap to open detail + tasks) |
| `/done <id>` | Mark task #id done |
| `/undo <id>` | Flip task back to pending |
| `/addproject Name \| category \| chain \| url` | Quick-add a project |
| `/addtask <project_id> \| Title \| cadence` | Quick-add a task |
| `/reset` | Manually reset all daily tasks |
| `/help` | Show this list |

The bot only answers your `TELEGRAM_CHAT_ID` — anyone else messaging it gets "Unauthorized".

### 📱 Running on Android (Termux)

This app is designed to run 24/7 on your phone. See **[TERMUX.md](./TERMUX.md)**
for the full step-by-step guide (covers Termux:Boot auto-start, wake-lock, and
Telegram setup).

Quick version:

```bash
pkg install -y python git rust binutils
git clone https://github.com/4bill/trading-bot.git
cd trading-bot/airdrop-manager
chmod +x start.sh
./start.sh --bg          # background, logs in logs/app.log
termux-wake-lock         # keep alive when screen is off
```

## ⚙️ Configuration

All settings come from environment variables (or the `.env` file). See
[`.env.example`](./.env.example) for the full list. Notable ones:

| Variable | Default | Purpose |
|----------|---------|---------|
| `WEBAPP_PORT` | `8090` | HTTP port |
| `DB_PATH` | `data/airdrop.db` | SQLite location (relative to this folder) |
| `TELEGRAM_BOT_TOKEN` | _(empty)_ | From [@BotFather](https://t.me/BotFather). Empty = reminders disabled. |
| `TELEGRAM_CHAT_ID` | _(empty)_ | Your numeric id (use [@userinfobot](https://t.me/userinfobot)) |
| `REMINDER_TIMES` | `08:00,20:00` | Comma-separated 24h times |
| `DAILY_RESET_TIME` | `00:05` | When `daily` tasks become pending again |
| `TIMEZONE` | `Asia/Jakarta` | IANA timezone for all crons |

## 🗂 Project layout

```
airdrop-manager/
├── app.py                   # FastAPI entry + APScheduler lifespan
├── airdrop_mgr/
│   ├── config.py            # pydantic-settings
│   ├── db.py                # SQLite connect + schema
│   ├── store.py             # CRUD helpers
│   ├── scheduler.py         # daily reset + reminder cron jobs
│   ├── notifier.py          # Telegram summary builder + sender
│   └── webapp.py            # FastAPI app factory + REST routes
├── static/
│   ├── index.html           # Dashboard, Projects, Wallets, Settings tabs
│   └── app.js
├── requirements.txt
└── .env.example
```

## 📡 REST API (for power users)

| Method | Path | Description |
|--------|------|-------------|
| GET    | `/api/summary` | Counts: pending / done / total + per-category |
| GET    | `/api/projects` | List projects (`?include_archived=true` to include) |
| POST   | `/api/projects` | Create project |
| PATCH  | `/api/projects/{id}` | Partial update (incl. `archived`) |
| DELETE | `/api/projects/{id}` | Delete project + cascade tasks |
| GET    | `/api/wallets` | List wallets |
| POST   | `/api/wallets` | Create wallet |
| DELETE | `/api/wallets/{id}` | Delete wallet |
| GET    | `/api/tasks` | List tasks (`?project_id=` or `?status=pending`) |
| POST   | `/api/tasks` | Create task |
| POST   | `/api/tasks/{id}/done` | Mark done (`tx_hash`, `gas_used`, `notes`) |
| POST   | `/api/tasks/{id}/undo` | Mark pending again |
| DELETE | `/api/tasks/{id}` | Delete task |
| POST   | `/api/admin/reset-daily` | Manually reset daily tasks |
| POST   | `/api/notify/test` | Send a test Telegram summary |

## 🛣 Roadmap

- Per-task tx-hash & gas tracking UI (data model already supports it)
- Import / export project list as YAML
- Optional read-only on-chain status check via public RPC (no signing)
- Multi-user / auth (currently meant to run on your own machine)
