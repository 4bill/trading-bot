"""FastAPI app: serves dashboard UI + JSON API."""
from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import store
from .db import init_db
from .notifier import build_summary_message, send_telegram

log = logging.getLogger("airdrop_mgr.webapp")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(ROOT, "static")


# ---------- payloads ----------
class ProjectIn(BaseModel):
    name: str = Field(min_length=1)
    category: str = Field(pattern="^(testnet|bridge_swap|daily_claim|other)$")
    chain: Optional[str] = None
    url: Optional[str] = None
    notes: Optional[str] = None
    priority: int = Field(default=2, ge=1, le=3)


class ProjectPatch(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = Field(default=None, pattern="^(testnet|bridge_swap|daily_claim|other)$")
    chain: Optional[str] = None
    url: Optional[str] = None
    notes: Optional[str] = None
    priority: Optional[int] = Field(default=None, ge=1, le=3)
    archived: Optional[int] = Field(default=None, ge=0, le=1)


class WalletIn(BaseModel):
    label: str = Field(min_length=1)
    address: str = Field(min_length=4)
    chain: Optional[str] = None
    notes: Optional[str] = None


class TaskIn(BaseModel):
    project_id: int
    title: str = Field(min_length=1)
    cadence: str = Field(default="daily", pattern="^(daily|weekly|once)$")
    wallet_id: Optional[int] = None
    notes: Optional[str] = None


class TaskDone(BaseModel):
    tx_hash: Optional[str] = None
    gas_used: Optional[float] = None
    notes: Optional[str] = None


# ---------- app factory ----------
def create_app() -> FastAPI:
    init_db()
    app = FastAPI(title="Airdrop manager", version="0.1.0")

    if os.path.isdir(STATIC_DIR):
        app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    def index():
        idx = os.path.join(STATIC_DIR, "index.html")
        if os.path.exists(idx):
            return FileResponse(idx)
        return {"ok": True, "msg": "static/index.html missing"}

    @app.get("/healthz")
    def healthz():
        return {"ok": True}

    # ----- projects -----
    @app.get("/api/projects")
    def api_list_projects(include_archived: bool = False):
        return store.list_projects(include_archived=include_archived)

    @app.post("/api/projects")
    def api_create_project(payload: ProjectIn):
        pid = store.create_project(**payload.model_dump())
        return {"id": pid}

    @app.patch("/api/projects/{project_id}")
    def api_update_project(project_id: int, payload: ProjectPatch):
        fields = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not fields:
            raise HTTPException(status_code=400, detail="no fields to update")
        store.update_project(project_id, **fields)
        return {"ok": True}

    @app.delete("/api/projects/{project_id}")
    def api_delete_project(project_id: int):
        store.delete_project(project_id)
        return {"ok": True}

    # ----- wallets -----
    @app.get("/api/wallets")
    def api_list_wallets():
        return store.list_wallets()

    @app.post("/api/wallets")
    def api_create_wallet(payload: WalletIn):
        try:
            wid = store.create_wallet(**payload.model_dump())
        except Exception as e:  # likely UNIQUE constraint
            raise HTTPException(status_code=400, detail=str(e)) from e
        return {"id": wid}

    @app.delete("/api/wallets/{wallet_id}")
    def api_delete_wallet(wallet_id: int):
        store.delete_wallet(wallet_id)
        return {"ok": True}

    # ----- tasks -----
    @app.get("/api/tasks")
    def api_list_tasks(project_id: Optional[int] = None, status: Optional[str] = None):
        return store.list_tasks(project_id=project_id, status=status)

    @app.post("/api/tasks")
    def api_create_task(payload: TaskIn):
        tid = store.create_task(**payload.model_dump())
        return {"id": tid}

    @app.delete("/api/tasks/{task_id}")
    def api_delete_task(task_id: int):
        store.delete_task(task_id)
        return {"ok": True}

    @app.post("/api/tasks/{task_id}/done")
    def api_task_done(task_id: int, payload: TaskDone):
        store.mark_task_done(
            task_id,
            tx_hash=payload.tx_hash,
            gas_used=payload.gas_used,
            notes=payload.notes,
        )
        return {"ok": True}

    @app.post("/api/tasks/{task_id}/undo")
    def api_task_undo(task_id: int):
        store.update_task(task_id, status="pending")
        return {"ok": True}

    @app.post("/api/admin/reset-daily")
    def api_reset_daily():
        n = store.reset_daily_tasks()
        return {"reset": n}

    # ----- summary -----
    @app.get("/api/summary")
    def api_summary():
        return store.daily_summary()

    @app.post("/api/notify/test")
    async def api_notify_test():
        msg = build_summary_message()
        result = await send_telegram(msg)
        return JSONResponse({"sent": bool(result), "preview": msg})

    return app
