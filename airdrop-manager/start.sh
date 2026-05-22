#!/usr/bin/env bash
# One-shot launcher for the airdrop manager.
# Works on Linux, macOS, and Termux (Android).
#
# Usage:
#   ./start.sh            # foreground
#   ./start.sh --bg       # background (writes logs/app.log, pid file)
#   ./start.sh --stop     # stop the background instance
#   ./start.sh --status   # show whether it's running

set -e
cd "$(dirname "$0")"

PIDFILE="data/app.pid"
LOGFILE="logs/app.log"
mkdir -p data logs

start_foreground() {
  bootstrap_venv
  echo ">> starting airdrop-manager (foreground)..."
  exec .venv/bin/python app.py
}

start_background() {
  if is_running; then
    echo ">> already running (pid $(cat "$PIDFILE"))"
    exit 0
  fi
  bootstrap_venv
  echo ">> starting airdrop-manager (background)..."
  # On Termux this keeps it alive when screen is off (paired with termux-wake-lock).
  nohup .venv/bin/python app.py >> "$LOGFILE" 2>&1 &
  echo $! > "$PIDFILE"
  sleep 1
  echo ">> pid $(cat "$PIDFILE")  ·  log: $LOGFILE"
}

stop_background() {
  if ! is_running; then
    echo ">> not running"
    rm -f "$PIDFILE"
    exit 0
  fi
  pid=$(cat "$PIDFILE")
  kill "$pid" 2>/dev/null || true
  for _ in 1 2 3 4 5; do
    if ! kill -0 "$pid" 2>/dev/null; then break; fi
    sleep 1
  done
  rm -f "$PIDFILE"
  echo ">> stopped"
}

status() {
  if is_running; then
    echo ">> running (pid $(cat "$PIDFILE"))"
  else
    echo ">> not running"
  fi
}

is_running() {
  [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null
}

bootstrap_venv() {
  if [ ! -d ".venv" ]; then
    echo ">> creating virtualenv (.venv)..."
    python3 -m venv .venv
    .venv/bin/pip install --upgrade pip --quiet
    echo ">> installing requirements..."
    .venv/bin/pip install -r requirements.txt
  fi
  if [ ! -f ".env" ]; then
    echo ">> .env not found - copying from .env.example"
    cp .env.example .env
    echo "   edit .env to set TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID, then re-run."
  fi
}

case "${1:-}" in
  --bg|-d)        start_background ;;
  --stop)         stop_background ;;
  --status)       status ;;
  --help|-h)      sed -n '2,11p' "$0" ;;
  *)              start_foreground ;;
esac
