"""Entry point: FastAPI dashboard + APScheduler (daily reset & reminders)."""
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

from airdrop_mgr.config import get_settings  # noqa: E402
from airdrop_mgr.scheduler import build_scheduler  # noqa: E402
from airdrop_mgr.webapp import create_app  # noqa: E402

app = create_app()
_scheduler = None


@asynccontextmanager
async def lifespan(_app):
    global _scheduler
    _scheduler = build_scheduler()
    _scheduler.start()
    log.info("Scheduler started; jobs: %s", [j.id for j in _scheduler.get_jobs()])
    try:
        yield
    finally:
        if _scheduler:
            _scheduler.shutdown(wait=False)


app.router.lifespan_context = lifespan


if __name__ == "__main__":
    import uvicorn

    s = get_settings()
    port = int(os.getenv("PORT", str(s.webapp_port)))
    uvicorn.run("app:app", host=s.webapp_host, port=port)
