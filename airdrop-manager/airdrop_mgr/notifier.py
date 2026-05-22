"""Telegram notifier (optional). Uses raw HTTPS API via httpx — no aiogram dep."""
from __future__ import annotations

import logging
from typing import Optional

import httpx

from .config import get_settings
from .store import daily_summary, list_tasks

log = logging.getLogger("airdrop_mgr.notifier")

CATEGORY_LABEL = {
    "testnet": "Testnet",
    "bridge_swap": "Bridge / Swap",
    "daily_claim": "Daily Claim",
    "other": "Other",
}


async def send_telegram(text: str) -> Optional[dict]:
    s = get_settings()
    if not s.telegram_enabled:
        log.debug("Telegram disabled; skipping send.")
        return None
    url = f"https://api.telegram.org/bot{s.telegram_bot_token}/sendMessage"
    payload = {
        "chat_id": s.telegram_chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(url, json=payload)
        if r.status_code != 200:
            log.warning("Telegram send failed: %s %s", r.status_code, r.text)
            return None
        return r.json()


def build_summary_message() -> str:
    summary = daily_summary()
    pending = summary["pending"]
    done = summary["done"]
    total = summary["total"]

    lines = ["<b>🪂 Airdrop Daily Summary</b>", ""]
    if total == 0:
        lines.append("No tasks yet. Add some projects in the dashboard!")
        return "\n".join(lines)

    pct = int(round((done / total) * 100)) if total else 0
    lines.append(f"Progress: <b>{done}/{total}</b> ({pct}%)")
    lines.append(f"Pending: <b>{pending}</b>  ·  Done: <b>{done}</b>")
    lines.append("")

    for entry in summary["per_category"]:
        label = CATEGORY_LABEL.get(entry["category"], entry["category"])
        lines.append(f"• {label}: {entry['done'] or 0} done / {entry['pending'] or 0} pending")

    if pending > 0:
        lines.append("")
        lines.append("<b>Top pending:</b>")
        pending_tasks = [t for t in list_tasks(status="pending")][:8]
        for t in pending_tasks:
            chain = f" [{t['project_chain']}]" if t.get("project_chain") else ""
            lines.append(f"– {t['project_name']}{chain}: {t['title']}")
    return "\n".join(lines)


async def send_daily_summary() -> None:
    await send_telegram(build_summary_message())
