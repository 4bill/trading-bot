"""SQLite connection + schema bootstrap.

Schema:
- projects:    airdrop projects you are farming (name, category, chain, ...)
- wallets:     wallet labels & addresses (NEVER store private keys here)
- tasks:       per-project tasks (daily check-in, swap, bridge, ...)
- task_logs:   history of completed task executions (audit trail)
"""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from typing import Iterator

from .config import get_settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    category    TEXT NOT NULL CHECK (category IN ('testnet', 'bridge_swap', 'daily_claim', 'other')),
    chain       TEXT,
    url         TEXT,
    notes       TEXT,
    priority    INTEGER NOT NULL DEFAULT 2,  -- 1=high, 2=medium, 3=low
    archived    INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS wallets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    label       TEXT NOT NULL,
    address     TEXT NOT NULL,
    chain       TEXT,
    notes       TEXT,
    archived    INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (address, chain)
);

CREATE TABLE IF NOT EXISTS tasks (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id   INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    wallet_id    INTEGER REFERENCES wallets(id) ON DELETE SET NULL,
    title        TEXT NOT NULL,
    cadence      TEXT NOT NULL CHECK (cadence IN ('daily', 'weekly', 'once')) DEFAULT 'daily',
    status       TEXT NOT NULL CHECK (status IN ('pending', 'done', 'skipped')) DEFAULT 'pending',
    last_done_at TEXT,
    notes        TEXT,
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS task_logs (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id   INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    done_at   TEXT NOT NULL DEFAULT (datetime('now')),
    tx_hash   TEXT,
    gas_used  REAL,
    notes     TEXT
);

CREATE INDEX IF NOT EXISTS idx_tasks_project    ON tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status     ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_task_logs_task   ON task_logs(task_id);
CREATE INDEX IF NOT EXISTS idx_projects_archive ON projects(archived);
"""


def _resolve_path(path: str) -> str:
    """Resolve relative DB path against the project root (parent of airdrop_mgr/)."""
    if os.path.isabs(path):
        return path
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(here, path)


def _ensure_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    db_path = _resolve_path(get_settings().db_path)
    _ensure_dir(db_path)
    conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create tables if they don't exist."""
    with connect() as conn:
        conn.executescript(SCHEMA)
