# 🪂 Airdrop Manager

Lightweight FastAPI dashboard to track 15+ crypto airdrop projects across multiple
wallets without losing your sanity.

Built for the **testnet / bridge-swap / daily-claim** kind of farming workflow:
add your projects once, define their daily tasks, then just tap ✓ as you finish them.
Telegram reminders ping you twice a day so nothing slips through.

## ✨ Features

- **Project tracker** with categories (Testnet / Bridge-Swap / Daily Claim / Other), chain, priority and notes
- **Multi-wallet** support (only public addresses + labels — *never* private keys)
- **Tasks** with `daily` / `weekly` / `once` cadence
- **One-tap done/undo** plus an audit log of every completion
- **Auto daily reset** at 00:05 (configurable) so daily tasks come back tomorrow
- **Telegram reminders** at 08:00 and 20:00 (configurable) with a category breakdown
- Pure FastAPI + SQLite + vanilla JS — no build step, runs on any cheap VPS / Render / Railway

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
few tasks, and you're done.

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
