"""CRUD layer on top of SQLite. Returns plain dicts for easy JSON serialisation."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .db import connect


# ---------- helpers ----------
def _row_to_dict(row) -> Dict[str, Any]:
    return {k: row[k] for k in row.keys()}


# ---------- projects ----------
def list_projects(include_archived: bool = False) -> List[Dict[str, Any]]:
    sql = "SELECT * FROM projects"
    if not include_archived:
        sql += " WHERE archived = 0"
    sql += " ORDER BY priority ASC, name ASC"
    with connect() as conn:
        return [_row_to_dict(r) for r in conn.execute(sql)]


def create_project(
    *,
    name: str,
    category: str,
    chain: Optional[str] = None,
    url: Optional[str] = None,
    notes: Optional[str] = None,
    priority: int = 2,
) -> int:
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO projects (name, category, chain, url, notes, priority) VALUES (?,?,?,?,?,?)",
            (name, category, chain, url, notes, priority),
        )
        return cur.lastrowid


def update_project(project_id: int, **fields: Any) -> None:
    if not fields:
        return
    cols = ", ".join(f"{k}=?" for k in fields)
    values = list(fields.values()) + [project_id]
    with connect() as conn:
        conn.execute(f"UPDATE projects SET {cols} WHERE id=?", values)


def delete_project(project_id: int) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM projects WHERE id=?", (project_id,))


# ---------- wallets ----------
def list_wallets(include_archived: bool = False) -> List[Dict[str, Any]]:
    sql = "SELECT * FROM wallets"
    if not include_archived:
        sql += " WHERE archived = 0"
    sql += " ORDER BY label ASC"
    with connect() as conn:
        return [_row_to_dict(r) for r in conn.execute(sql)]


def create_wallet(
    *,
    label: str,
    address: str,
    chain: Optional[str] = None,
    notes: Optional[str] = None,
) -> int:
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO wallets (label, address, chain, notes) VALUES (?,?,?,?)",
            (label, address, chain, notes),
        )
        return cur.lastrowid


def delete_wallet(wallet_id: int) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM wallets WHERE id=?", (wallet_id,))


# ---------- tasks ----------
def list_tasks(
    *,
    project_id: Optional[int] = None,
    status: Optional[str] = None,
) -> List[Dict[str, Any]]:
    sql = (
        "SELECT t.*, p.name AS project_name, p.category AS project_category, "
        "p.chain AS project_chain, w.label AS wallet_label, w.address AS wallet_address "
        "FROM tasks t "
        "JOIN projects p ON p.id = t.project_id "
        "LEFT JOIN wallets w ON w.id = t.wallet_id "
        "WHERE p.archived = 0"
    )
    args: List[Any] = []
    if project_id is not None:
        sql += " AND t.project_id = ?"
        args.append(project_id)
    if status:
        sql += " AND t.status = ?"
        args.append(status)
    sql += " ORDER BY p.priority ASC, p.name ASC, t.id ASC"
    with connect() as conn:
        return [_row_to_dict(r) for r in conn.execute(sql, args)]


def create_task(
    *,
    project_id: int,
    title: str,
    cadence: str = "daily",
    wallet_id: Optional[int] = None,
    notes: Optional[str] = None,
) -> int:
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO tasks (project_id, wallet_id, title, cadence, notes) VALUES (?,?,?,?,?)",
            (project_id, wallet_id, title, cadence, notes),
        )
        return cur.lastrowid


def update_task(task_id: int, **fields: Any) -> None:
    if not fields:
        return
    cols = ", ".join(f"{k}=?" for k in fields)
    values = list(fields.values()) + [task_id]
    with connect() as conn:
        conn.execute(f"UPDATE tasks SET {cols} WHERE id=?", values)


def delete_task(task_id: int) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))


def mark_task_done(
    task_id: int,
    *,
    tx_hash: Optional[str] = None,
    gas_used: Optional[float] = None,
    notes: Optional[str] = None,
) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE tasks SET status='done', last_done_at=datetime('now') WHERE id=?",
            (task_id,),
        )
        conn.execute(
            "INSERT INTO task_logs (task_id, tx_hash, gas_used, notes) VALUES (?,?,?,?)",
            (task_id, tx_hash, gas_used, notes),
        )


def reset_daily_tasks() -> int:
    """Mark all 'done' daily tasks back to 'pending'. Returns rows affected."""
    with connect() as conn:
        cur = conn.execute(
            "UPDATE tasks SET status='pending' WHERE cadence='daily' AND status='done'"
        )
        return cur.rowcount


# ---------- aggregates ----------
def daily_summary() -> Dict[str, Any]:
    """Return counts useful for dashboard + Telegram reminder."""
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                SUM(CASE WHEN t.status='pending' THEN 1 ELSE 0 END) AS pending,
                SUM(CASE WHEN t.status='done' THEN 1 ELSE 0 END)    AS done,
                COUNT(*)                                            AS total
            FROM tasks t
            JOIN projects p ON p.id = t.project_id
            WHERE p.archived = 0
            """
        ).fetchone()
        per_category = conn.execute(
            """
            SELECT p.category AS category,
                   SUM(CASE WHEN t.status='pending' THEN 1 ELSE 0 END) AS pending,
                   SUM(CASE WHEN t.status='done' THEN 1 ELSE 0 END)    AS done
            FROM tasks t
            JOIN projects p ON p.id = t.project_id
            WHERE p.archived = 0
            GROUP BY p.category
            """
        ).fetchall()
    return {
        "pending": row["pending"] or 0,
        "done": row["done"] or 0,
        "total": row["total"] or 0,
        "per_category": [_row_to_dict(r) for r in per_category],
    }
