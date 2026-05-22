# 📱 Running on Android with Termux

This guide gets the airdrop manager running 24/7 on your phone. After setup
you'll have **two ways to use it**:

1. **Telegram bot** (primary) — DM your bot, tap `/today` and inline buttons to
   mark tasks done. No need to keep a browser tab open.
2. **Web dashboard** at `http://localhost:8090` — handy for bulk-adding the
   first 15 projects via forms.

Plus auto reminders twice a day. Everything survives screen-off and reboots.

> ⚠️ **Install Termux from F-Droid, NOT the Play Store.**
> The Play Store version is outdated and broken. Get it here:
> [F-Droid · Termux](https://f-droid.org/en/packages/com.termux/)

---

## 1. Install Termux + helpers

From F-Droid, install all three (free):

| App | Why you need it |
|-----|-----------------|
| **Termux** | The terminal itself |
| **Termux:Boot** | Auto-start the app when phone reboots |
| **Termux:API** | (optional) Native Android notifications |

Open Termux once so it finishes setup, then in Android Settings give Termux
**battery optimization → Don't optimize** (otherwise Android will kill it after
a few hours of screen-off).

---

## 2. Set up the environment

In Termux:

```bash
# Update packages and install Python + git
pkg update -y && pkg upgrade -y
pkg install -y python git rust binutils

# Allow Termux to read your phone storage (for backups)
termux-setup-storage

# Clone the repo
git clone https://github.com/4bill/trading-bot.git
cd trading-bot/airdrop-manager

# First-time install (also creates .env from the example)
chmod +x start.sh
./start.sh --status   # bootstrap the venv on first start
```

> `rust` and `binutils` are needed because pydantic v2 builds a small native
> core. The first `pip install` takes ~3-5 minutes on a phone — be patient.

---

## 3. Configure Telegram (recommended)

Even if you keep the phone on, Telegram reminders help when the dashboard isn't
open.

```bash
nano .env
```

Set:
```
TELEGRAM_BOT_TOKEN=...   # from @BotFather
TELEGRAM_CHAT_ID=...     # from @userinfobot
TIMEZONE=Asia/Jakarta
REMINDER_TIMES=08:00,20:00
```

Save with `Ctrl+O`, `Enter`, then `Ctrl+X`.

---

## 4. Run it

**Foreground (testing):**
```bash
./start.sh
```

You should see logs like `Scheduler started` and `Telegram bot started (long-polling)`.

Now you can use it two ways:

**(a) Via Telegram (recommended for daily ops)** — open Telegram, find your bot,
send `/start`, then `/today` to see pending tasks with tap-to-done buttons.
See the [bot commands table](./README.md#-telegram-bot-commands) in the README.

**(b) Via the web dashboard** — open Chrome / Firefox on the same phone →
`http://localhost:8090`. Tabs: **Dashboard**, **Projects**, **Wallets**,
**Settings**. Best for bulk-adding the first 15 projects (a form is faster
than typing slash commands on a phone keyboard).

Press `Ctrl+C` to stop.

**Background (real usage):**
```bash
termux-wake-lock     # keep CPU alive when screen is off
./start.sh --bg      # writes logs to logs/app.log

./start.sh --status  # check
./start.sh --stop    # stop
tail -f logs/app.log # watch logs
```

`termux-wake-lock` is the magic that prevents Android from suspending Python.
Run it once per Termux session. To release later: `termux-wake-unlock`.

---

## 5. Auto-start on phone reboot

With **Termux:Boot** installed, create a startup script:

```bash
mkdir -p ~/.termux/boot
cat > ~/.termux/boot/start-airdrop <<'EOF'
#!/data/data/com.termux/files/usr/bin/sh
termux-wake-lock
cd ~/trading-bot/airdrop-manager
./start.sh --bg
EOF
chmod +x ~/.termux/boot/start-airdrop
```

Open the **Termux:Boot** app once (just opening it is enough — it activates the
hook). Now after every reboot the app comes up automatically.

---

## 6. (Optional) Access from your laptop / other phones

By default the app listens on `0.0.0.0:8090`, so any device on the **same
Wi-Fi** can reach it:

```bash
ifconfig wlan0 | grep inet     # find the phone's local IP, e.g. 192.168.1.42
```

Then on your laptop browser: `http://192.168.1.42:8090`.

If you want access from outside your home Wi-Fi, use **Cloudflare Tunnel** or
**Tailscale** rather than opening ports. Don't expose this app to the public
internet without auth — it's single-user only right now.

---

## 7. Updating

```bash
cd ~/trading-bot
git pull
cd airdrop-manager
./start.sh --stop
.venv/bin/pip install -r requirements.txt   # only if requirements changed
./start.sh --bg
```

Your SQLite database (`data/airdrop.db`) is untouched by updates.

---

## Troubleshooting

**`pip install` fails on `pydantic-core`**
Make sure `rust` and `binutils` are installed: `pkg install rust binutils`.
On older Android versions, also try `pkg install build-essential`.

**App stops after a few hours**
You forgot `termux-wake-lock`, or Android killed Termux for battery reasons.
Whitelist Termux from battery optimisation in Android settings.

**Browser shows "site can't be reached"**
The app might still be installing on first run. Check `tail -f logs/app.log`.
If it says `Address already in use`, run `./start.sh --stop` first.

**Telegram reminders don't arrive**
- Test from the dashboard → Settings → "Send test summary"
- Check `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env`
- Make sure you've sent **at least one message** to your bot first (Telegram
  bots can't initiate conversations).

**Bot replies "Unauthorized" to my messages**
Your `TELEGRAM_CHAT_ID` doesn't match. Send a message to
[@userinfobot](https://t.me/userinfobot) and copy the numeric `Id` it shows
into your `.env`, then restart with `./start.sh --stop && ./start.sh --bg`.

**Bot doesn't respond at all**
- Check `tail -f logs/app.log` for `Telegram bot started (long-polling)`
- If it says "bot disabled (no TELEGRAM_BOT_TOKEN)", your `.env` is missing the token
- Only one process can long-poll a bot at a time. Make sure you don't have a
  duplicate instance still running: `./start.sh --status`

**Phone gets warm**
Normal — Python is alive 24/7. The CPU usage is essentially 0% when idle (the
scheduler only wakes up at reset/reminder times). Disk I/O is also minimal.
