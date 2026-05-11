"""Single-process entrypoint: runs the FastAPI webapp AND the Telegram bot together.

Designed for phone-friendly cloud hosting (Render, Railway, Fly.io, etc.)
where you only get one long-running process per service.

Start command:
    python app.py
or equivalently:
    uvicorn app:app --host 0.0.0.0 --port $PORT
"""
from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("app")

# Import the already-built FastAPI app and the aiogram Dispatcher.
from webapp.main import app  # noqa: E402
from bot.main import dp, BOT_TOKEN  # noqa: E402

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

_bot_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(_app):
    """Start the Telegram bot in the background while the webapp serves HTTP."""
    global _bot_task
    if BOT_TOKEN:
        bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

        async def _run():
            log.info("Starting Telegram bot polling")
            try:
                await dp.start_polling(bot, handle_signals=False)
            except Exception:  # noqa: BLE001
                log.exception("Bot polling crashed")
            finally:
                await bot.session.close()

        _bot_task = asyncio.create_task(_run())
    else:
        log.warning("TELEGRAM_BOT_TOKEN not set; running webapp only.")
    try:
        yield
    finally:
        if _bot_task and not _bot_task.done():
            _bot_task.cancel()
            try:
                await _bot_task
            except (asyncio.CancelledError, Exception):
                pass


# Attach the lifespan to the imported FastAPI app.
app.router.lifespan_context = lifespan


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", os.getenv("WEBAPP_PORT", "8080")))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
