"""Entry point: FastAPI dashboard + Telegram bot + APScheduler.

The Telegram bot is the *primary* interface for daily ops on mobile (tap-to-done,
summaries, quick add). The web dashboard at :8090 is kept for bulk setup.
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("airdrop_mgr.app")

from airdrop_mgr.bot import build_application, configure_commands  # noqa: E402
from airdrop_mgr.config import get_settings  # noqa: E402
from airdrop_mgr.scheduler import build_scheduler  # noqa: E402
from airdrop_mgr.webapp import create_app  # noqa: E402


app = create_app()


@asynccontextmanager
async def lifespan(_app):
    scheduler = build_scheduler()
    scheduler.start()
    log.info("Scheduler started; jobs: %s", [j.id for j in scheduler.get_jobs()])

    tg_app = build_application()
    if tg_app is not None:
        await tg_app.initialize()
        await configure_commands(tg_app)
        await tg_app.start()
        await tg_app.updater.start_polling(drop_pending_updates=True)
        log.info("Telegram bot started (long-polling).")
    else:
        log.info("Telegram bot disabled (no TELEGRAM_BOT_TOKEN).")

    try:
        yield
    finally:
        if tg_app is not None:
            try:
                await tg_app.updater.stop()
                await tg_app.stop()
                await tg_app.shutdown()
            except Exception as e:  # pragma: no cover
                log.warning("Telegram shutdown error: %s", e)
        try:
            scheduler.shutdown(wait=False)
        except Exception as e:  # pragma: no cover
            log.warning("Scheduler shutdown error: %s", e)


app.router.lifespan_context = lifespan


if __name__ == "__main__":
    import uvicorn

    s = get_settings()
    port = int(os.getenv("PORT", str(s.webapp_port)))
    uvicorn.run("app:app", host=s.webapp_host, port=port)
