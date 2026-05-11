"""Telegram bot: shows a button that opens the Mini App form.
When the form submits, the bot receives a compact summary via `web_app_data`.

Run:
    python -m bot.main
"""
from __future__ import annotations

import asyncio
import json
import logging
import os

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import (
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    WebAppInfo,
)
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("bot")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
WEBAPP_URL = os.getenv("WEBAPP_URL", "").strip()

if not BOT_TOKEN:
    raise SystemExit("TELEGRAM_BOT_TOKEN is not set. Put it in .env")
if not WEBAPP_URL.startswith("https://"):
    raise SystemExit("WEBAPP_URL must be an https:// URL (Telegram requires HTTPS for Mini Apps).")

dp = Dispatcher()


def main_keyboard() -> ReplyKeyboardMarkup:
    form_url = WEBAPP_URL.rstrip("/") + "/static/index.html"
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Open trading form", web_app=WebAppInfo(url=form_url))]],
        resize_keyboard=True,
    )


@dp.message(CommandStart())
async def on_start(message: Message) -> None:
    await message.answer(
        "<b>Trading bot</b>\n\n"
        "Tap the button below to open the form. You can:\n"
        "• <b>Analyze</b> a symbol (RSI + EMA cross)\n"
        "• <b>Auto-trade</b> on your chosen exchange\n\n"
        "Use the exchange <i>testnet</i> while you're learning.",
        reply_markup=main_keyboard(),
    )


@dp.message(F.web_app_data)
async def on_webapp_data(message: Message) -> None:
    """Receives the compact JSON the Mini App sends via Telegram.WebApp.sendData()."""
    raw = message.web_app_data.data
    try:
        payload = json.loads(raw)
    except Exception:
        await message.answer(f"Got raw data:\n<code>{raw}</code>")
        return

    mode = payload.get("mode", "?")
    sym = payload.get("symbol", "?")
    tf = payload.get("timeframe", "?")
    signal = payload.get("signal", "?")
    trade_ok = payload.get("trade_ok")

    lines = [
        f"<b>Submission</b>",
        f"Mode: <code>{mode}</code>",
        f"Symbol: <code>{sym}</code> ({tf})",
        f"Signal: <b>{signal}</b>",
    ]
    if trade_ok is True:
        lines.append("Trade: ✅ placed")
    elif trade_ok is False:
        lines.append("Trade: ❌ failed (see form)")

    await message.answer("\n".join(lines), reply_markup=ReplyKeyboardRemove())


@dp.message()
async def on_any(message: Message) -> None:
    await message.answer("Tap the button to open the form.", reply_markup=main_keyboard())


async def main() -> None:
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    log.info("Bot starting; webapp URL = %s", WEBAPP_URL)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
