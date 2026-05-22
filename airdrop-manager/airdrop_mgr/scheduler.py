"""Background scheduling: daily task reset + reminder pings."""
from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .config import get_settings
from .notifier import send_daily_summary
from .store import reset_daily_tasks

log = logging.getLogger("airdrop_mgr.scheduler")


def _parse_hhmm(value: str) -> tuple[int, int]:
    hh, mm = value.split(":")
    return int(hh), int(mm)


def build_scheduler() -> AsyncIOScheduler:
    s = get_settings()
    scheduler = AsyncIOScheduler(timezone=s.timezone)

    # Daily reset of all 'daily' tasks back to pending
    rh, rm = _parse_hhmm(s.daily_reset_time)
    scheduler.add_job(
        _job_daily_reset,
        CronTrigger(hour=rh, minute=rm, timezone=s.timezone),
        id="daily_reset",
        replace_existing=True,
    )

    # Reminder pushes
    for idx, hhmm in enumerate(s.reminder_time_list):
        rh, rm = _parse_hhmm(hhmm)
        scheduler.add_job(
            send_daily_summary,
            CronTrigger(hour=rh, minute=rm, timezone=s.timezone),
            id=f"reminder_{idx}",
            replace_existing=True,
        )

    return scheduler


async def _job_daily_reset() -> None:
    n = reset_daily_tasks()
    log.info("Daily reset: %s task(s) returned to 'pending'", n)
