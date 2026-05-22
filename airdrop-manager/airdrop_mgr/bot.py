"""Telegram bot interface for the airdrop manager.

This is the primary interface for daily monitoring on mobile. The web dashboard
is still available for bulk setup (add 15 projects at once), but for the
day-to-day "tap done as I finish each task" loop the bot is much faster.

Commands:
- /start, /help     intro + command list
- /today            pending tasks today, grouped by project, with quick-done buttons
- /summary          today's progress (same content as the daily reminder)
- /projects         list projects (each becomes a button → details)
- /pending          flat list of all pending tasks (max 30)
- /done <id>        mark task #id done
- /undo <id>        flip a task back to pending
- /addproject <name> | <category> [| chain | url]    quick add
- /addtask <project_id> | <title> [| cadence]        quick add task
- /reset            manually reset all daily tasks
"""
from __future__ import annotations

import logging
from html import escape
from typing import List, Optional

from telegram import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from . import store
from .config import get_settings
from .notifier import CATEGORY_LABEL, build_summary_message

log = logging.getLogger("airdrop_mgr.bot")

VALID_CATEGORIES = {"testnet", "bridge_swap", "daily_claim", "other"}
VALID_CADENCES = {"daily", "weekly", "once"}
MAX_TASKS_IN_LIST = 30


# ---------- helpers ----------
def _is_authorized(update: Update) -> bool:
    """Restrict bot to the configured chat id (single-user)."""
    chat = update.effective_chat
    if chat is None:
        return False
    chat_id = str(chat.id)
    expected = str(get_settings().telegram_chat_id or "")
    if not expected:
        # no chat_id configured -> bot stays silent for safety
        return False
    return chat_id == expected


async def _deny(update: Update) -> None:
    if update.message:
        await update.message.reply_text("Unauthorized.")
    elif update.callback_query:
        await update.callback_query.answer("Unauthorized", show_alert=True)


def _task_button(task: dict) -> InlineKeyboardButton:
    """Render a single task as a tappable inline button."""
    icon = "✅" if task["status"] == "done" else "⬜"
    label = f"{icon} {task['title']}"
    if len(label) > 60:
        label = label[:57] + "…"
    if task["status"] == "done":
        return InlineKeyboardButton(label, callback_data=f"undo:{task['id']}")
    return InlineKeyboardButton(label, callback_data=f"done:{task['id']}")


def _project_card(project: dict, tasks: list) -> tuple[str, InlineKeyboardMarkup | None]:
    """Build the message text + inline keyboard for one project's task list."""
    chain = f" · {escape(project['chain'])}" if project.get("chain") else ""
    cat = CATEGORY_LABEL.get(project["category"], project["category"])
    header = f"<b>{escape(project['name'])}</b>{chain}\n<i>{cat}</i>"
    if project.get("url"):
        header += f"\n{escape(project['url'])}"

    if not tasks:
        return header + "\n\n<i>No tasks for this project.</i>", None

    done = sum(1 for t in tasks if t["status"] == "done")
    header += f"\n\n<b>{done}/{len(tasks)}</b> done"

    keyboard = [[_task_button(t)] for t in tasks]
    keyboard.append([InlineKeyboardButton("🔄 Refresh", callback_data=f"proj:{project['id']}")])
    return header, InlineKeyboardMarkup(keyboard)


# ---------- /start, /help ----------
HELP_TEXT = (
    "🪂 <b>Airdrop Manager</b>\n\n"
    "<b>Daily ops</b>\n"
    "/today – pending tasks (tap ⬜ to mark done)\n"
    "/summary – today's progress\n"
    "/pending – all pending tasks\n\n"
    "<b>Browse</b>\n"
    "/projects – your projects (tap to open)\n\n"
    "<b>Quick add</b>\n"
    "<code>/addproject Linea | testnet | Linea | https://linea.build</code>\n"
    "<code>/addtask 3 | Daily check-in | daily</code>\n\n"
    "<b>Other</b>\n"
    "/done &lt;id&gt; – mark task done by id\n"
    "/undo &lt;id&gt; – flip task back to pending\n"
    "/reset – reset all daily tasks\n"
)


async def cmd_start(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        await _deny(update)
        return
    await update.message.reply_text(HELP_TEXT, parse_mode=ParseMode.HTML)


# ---------- /summary ----------
async def cmd_summary(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        await _deny(update)
        return
    await update.message.reply_text(
        build_summary_message(),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


# ---------- /today ----------
async def cmd_today(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        await _deny(update)
        return
    tasks = store.list_tasks(status="pending")
    if not tasks:
        await update.message.reply_text("✨ All tasks done for today!")
        return

    # group by project
    by_project: dict[int, list] = {}
    for t in tasks:
        by_project.setdefault(t["project_id"], []).append(t)

    summary = store.daily_summary()
    pct = int(round((summary["done"] / summary["total"]) * 100)) if summary["total"] else 0
    await update.message.reply_text(
        f"<b>Today</b>: {summary['done']}/{summary['total']} done ({pct}%)\n"
        f"{len(tasks)} task(s) pending across {len(by_project)} project(s)",
        parse_mode=ParseMode.HTML,
    )

    for pid, ts in by_project.items():
        first = ts[0]
        project = {
            "id": pid,
            "name": first["project_name"],
            "category": first["project_category"],
            "chain": first.get("project_chain"),
            "url": None,
        }
        text, kb = _project_card(project, ts)
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
            disable_web_page_preview=True,
        )


# ---------- /pending ----------
async def cmd_pending(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        await _deny(update)
        return
    tasks = store.list_tasks(status="pending")[:MAX_TASKS_IN_LIST]
    if not tasks:
        await update.message.reply_text("✨ Nothing pending.")
        return
    lines = [f"<b>Pending tasks ({len(tasks)})</b>", ""]
    keyboard = []
    for t in tasks:
        lines.append(f"#{t['id']} · <b>{escape(t['project_name'])}</b>: {escape(t['title'])}")
        keyboard.append([_task_button(t)])
    await update.message.reply_text(
        "\n".join(lines),
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ---------- /projects ----------
async def cmd_projects(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        await _deny(update)
        return
    projects = store.list_projects()
    if not projects:
        await update.message.reply_text(
            "No projects yet. Use the web dashboard to bulk-add, or:\n"
            "<code>/addproject Name | category | chain | url</code>",
            parse_mode=ParseMode.HTML,
        )
        return
    keyboard = []
    for p in projects:
        cat = CATEGORY_LABEL.get(p["category"], p["category"])
        label = f"{p['name']} · {cat}"
        if len(label) > 60:
            label = label[:57] + "…"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"proj:{p['id']}")])
    await update.message.reply_text(
        f"<b>Projects ({len(projects)})</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ---------- /done <id>, /undo <id> ----------
async def cmd_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        await _deny(update)
        return
    if not context.args:
        await update.message.reply_text("Usage: <code>/done 12</code>", parse_mode=ParseMode.HTML)
        return
    try:
        tid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Task id must be a number.")
        return
    store.mark_task_done(tid)
    await update.message.reply_text(f"✅ Task #{tid} marked done.")


async def cmd_undo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        await _deny(update)
        return
    if not context.args:
        await update.message.reply_text("Usage: <code>/undo 12</code>", parse_mode=ParseMode.HTML)
        return
    try:
        tid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Task id must be a number.")
        return
    store.update_task(tid, status="pending")
    await update.message.reply_text(f"↩️ Task #{tid} back to pending.")


# ---------- /addproject ----------
async def cmd_add_project(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        await _deny(update)
        return
    raw = update.message.text.split(" ", 1)
    if len(raw) < 2:
        await update.message.reply_text(
            "Usage:\n<code>/addproject Name | category | chain | url</code>\n\n"
            f"Categories: {', '.join(sorted(VALID_CATEGORIES))}",
            parse_mode=ParseMode.HTML,
        )
        return
    parts = [p.strip() for p in raw[1].split("|")]
    if len(parts) < 2:
        await update.message.reply_text("Need at least <code>Name | category</code>.", parse_mode=ParseMode.HTML)
        return
    name, category = parts[0], parts[1].lower()
    chain = parts[2] if len(parts) > 2 and parts[2] else None
    url = parts[3] if len(parts) > 3 and parts[3] else None
    if category not in VALID_CATEGORIES:
        await update.message.reply_text(
            f"Unknown category '{escape(category)}'. Allowed: {', '.join(sorted(VALID_CATEGORIES))}",
            parse_mode=ParseMode.HTML,
        )
        return
    pid = store.create_project(name=name, category=category, chain=chain, url=url)
    await update.message.reply_text(
        f"✓ Created project #{pid} <b>{escape(name)}</b>.\n"
        f"Add tasks with: <code>/addtask {pid} | Daily check-in | daily</code>",
        parse_mode=ParseMode.HTML,
    )


# ---------- /addtask ----------
async def cmd_add_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        await _deny(update)
        return
    raw = update.message.text.split(" ", 1)
    if len(raw) < 2:
        await update.message.reply_text(
            "Usage:\n<code>/addtask &lt;project_id&gt; | Title | cadence</code>\n"
            "Cadence: daily | weekly | once",
            parse_mode=ParseMode.HTML,
        )
        return
    parts = [p.strip() for p in raw[1].split("|")]
    if len(parts) < 2:
        await update.message.reply_text("Need at least <code>project_id | Title</code>.", parse_mode=ParseMode.HTML)
        return
    try:
        pid = int(parts[0])
    except ValueError:
        await update.message.reply_text("project_id must be a number.")
        return
    title = parts[1]
    cadence = parts[2].lower() if len(parts) > 2 and parts[2] else "daily"
    if cadence not in VALID_CADENCES:
        await update.message.reply_text(f"Cadence must be one of: {', '.join(VALID_CADENCES)}")
        return
    tid = store.create_task(project_id=pid, title=title, cadence=cadence)
    await update.message.reply_text(f"✓ Task #{tid} created (cadence: {cadence}).")


# ---------- /reset ----------
async def cmd_reset(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        await _deny(update)
        return
    n = store.reset_daily_tasks()
    await update.message.reply_text(f"🔄 Reset {n} daily task(s) to pending.")


# ---------- callback queries (inline button taps) ----------
async def on_callback(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not _is_authorized(update):
        await query.answer("Unauthorized", show_alert=True)
        return
    data = query.data or ""
    try:
        action, payload = data.split(":", 1)
    except ValueError:
        await query.answer()
        return

    if action == "done":
        tid = int(payload)
        store.mark_task_done(tid)
        await query.answer("✓ Done!")
        await _refresh_task_message(query, tid)
        return

    if action == "undo":
        tid = int(payload)
        store.update_task(tid, status="pending")
        await query.answer("↩️ Pending")
        await _refresh_task_message(query, tid)
        return

    if action == "proj":
        pid = int(payload)
        await _send_project_card(query, pid)
        return

    await query.answer()


async def _refresh_task_message(query, task_id: int) -> None:
    """After a done/undo tap, refresh the message it came from."""
    # find the project this task belongs to
    tasks = [t for t in store.list_tasks() if t["id"] == task_id]
    if not tasks:
        try:
            await query.edit_message_text("Task no longer exists.")
        except Exception:
            pass
        return
    pid = tasks[0]["project_id"]
    project_tasks = store.list_tasks(project_id=pid)
    if not project_tasks:
        try:
            await query.edit_message_text("Project has no tasks.")
        except Exception:
            pass
        return
    first = project_tasks[0]
    project = {
        "id": pid,
        "name": first["project_name"],
        "category": first["project_category"],
        "chain": first.get("project_chain"),
        "url": None,
    }
    text, kb = _project_card(project, project_tasks)
    try:
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
            disable_web_page_preview=True,
        )
    except Exception as e:
        log.debug("edit_message_text failed (likely unchanged): %s", e)


async def _send_project_card(query, project_id: int) -> None:
    projects = [p for p in store.list_projects(include_archived=True) if p["id"] == project_id]
    if not projects:
        await query.answer("Project not found", show_alert=True)
        return
    project = projects[0]
    tasks = store.list_tasks(project_id=project_id)
    text, kb = _project_card(project, tasks)
    try:
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
            disable_web_page_preview=True,
        )
    except Exception:
        # e.g. message was sent by /projects (just a list); reply with new card
        await query.message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
            disable_web_page_preview=True,
        )
    await query.answer()


# ---------- application factory ----------
def build_application() -> Optional[Application]:
    """Return a configured Application, or None if Telegram is disabled."""
    s = get_settings()
    if not s.telegram_bot_token:
        log.info("TELEGRAM_BOT_TOKEN empty - bot disabled.")
        return None
    if not s.telegram_chat_id:
        log.warning("TELEGRAM_CHAT_ID empty - bot will refuse all messages.")
        # We still build it so the user can DM the bot once and see "Unauthorized";
        # they can then read the chat id from logs and configure properly.

    app = ApplicationBuilder().token(s.telegram_bot_token).build()

    app.add_handler(CommandHandler(["start", "help"], cmd_start))
    app.add_handler(CommandHandler("today", cmd_today))
    app.add_handler(CommandHandler("summary", cmd_summary))
    app.add_handler(CommandHandler("pending", cmd_pending))
    app.add_handler(CommandHandler("projects", cmd_projects))
    app.add_handler(CommandHandler("done", cmd_done))
    app.add_handler(CommandHandler("undo", cmd_undo))
    app.add_handler(CommandHandler("addproject", cmd_add_project))
    app.add_handler(CommandHandler("addtask", cmd_add_task))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CallbackQueryHandler(on_callback))

    return app


async def configure_commands(app: Application) -> None:
    """Set the menu of commands shown by Telegram clients (the '/' button)."""
    await app.bot.set_my_commands(
        [
            BotCommand("today", "Pending tasks today"),
            BotCommand("summary", "Today's progress"),
            BotCommand("pending", "All pending tasks"),
            BotCommand("projects", "Browse projects"),
            BotCommand("done", "Mark task done by id"),
            BotCommand("undo", "Mark task pending by id"),
            BotCommand("addproject", "Quick-add project"),
            BotCommand("addtask", "Quick-add task"),
            BotCommand("reset", "Reset all daily tasks"),
            BotCommand("help", "Show help"),
        ]
    )
