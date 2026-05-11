"""FastAPI app that serves the Telegram Mini App (HTML form) and executes
analyze / auto-trade requests from the bot or directly from the form.

Run locally:
    python -m webapp.main
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from typing import Literal, Optional
from urllib.parse import parse_qsl

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from core.analyzer import analyze
from core.trader import place_order

load_dotenv()

log = logging.getLogger("webapp")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
EXCHANGE = os.getenv("EXCHANGE", "binance")
EXCHANGE_TESTNET = os.getenv("EXCHANGE_TESTNET", "true").lower() == "true"
DEFAULT_API_KEY = os.getenv("EXCHANGE_API_KEY", "")
DEFAULT_API_SECRET = os.getenv("EXCHANGE_API_SECRET", "")

app = FastAPI(title="Trading bot webapp")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR, html=True), name="static")


# ---------- Telegram initData verification ----------
# https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
def verify_init_data(init_data: str, bot_token: str) -> Optional[dict]:
    if not init_data or not bot_token:
        return None
    try:
        parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    except Exception:
        return None
    received_hash = parsed.pop("hash", None)
    if not received_hash:
        return None
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calc_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calc_hash, received_hash):
        return None
    if "user" in parsed:
        try:
            parsed["user"] = json.loads(parsed["user"])
        except Exception:
            pass
    return parsed


# ---------- request / response schemas ----------
Mode = Literal["analyze", "auto_trade"]
Side = Literal["buy", "sell"]
Strategy = Literal["rsi_ema", "rsi", "ema_cross"]


class SubmitPayload(BaseModel):
    mode: Mode = "analyze"
    exchange: str = Field(default_factory=lambda: EXCHANGE)
    symbol: str = "BTC/USDT"
    timeframe: str = "1h"
    strategy: Strategy = "rsi_ema"
    side: Side = "buy"
    amount: float = Field(0.0, ge=0)
    stop_loss_pct: Optional[float] = Field(None, ge=0, le=100)
    take_profit_pct: Optional[float] = Field(None, ge=0, le=100)
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    testnet: bool = EXCHANGE_TESTNET
    init_data: Optional[str] = None  # Telegram WebApp.initData


# ---------- routes ----------
@app.get("/")
def root():
    return {"ok": True, "docs": "/docs", "form": "/static/index.html"}


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.post("/api/submit")
async def submit(payload: SubmitPayload, request: Request):
    log.info("submit mode=%s symbol=%s tf=%s strat=%s", payload.mode, payload.symbol, payload.timeframe, payload.strategy)

    # If opened from Telegram, validate initData; reject on mismatch.
    if payload.init_data and BOT_TOKEN:
        verified = verify_init_data(payload.init_data, BOT_TOKEN)
        if not verified:
            raise HTTPException(status_code=401, detail="Invalid Telegram initData")

    # Run analysis
    try:
        result = analyze(
            exchange=payload.exchange,
            symbol=payload.symbol,
            timeframe=payload.timeframe,
            strategy=payload.strategy,
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Analyze failed: {e}") from e

    response = {"analysis": result.to_dict(), "trade": None}

    if payload.mode == "auto_trade":
        api_key = payload.api_key or DEFAULT_API_KEY
        api_secret = payload.api_secret or DEFAULT_API_SECRET
        if not api_key or not api_secret:
            raise HTTPException(status_code=400, detail="API key/secret required for auto_trade")
        if payload.amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be > 0 for auto_trade")

        # Option: only trade when signal matches side. Here we honor the user's chosen side.
        trade = place_order(
            exchange=payload.exchange,
            api_key=api_key,
            api_secret=api_secret,
            testnet=payload.testnet,
            symbol=payload.symbol,
            side=payload.side,
            amount=payload.amount,
            stop_loss_pct=payload.stop_loss_pct,
            take_profit_pct=payload.take_profit_pct,
        )
        response["trade"] = trade.to_dict()

    return JSONResponse(response)


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("WEBAPP_HOST", "0.0.0.0")
    port = int(os.getenv("WEBAPP_PORT", "8080"))
    uvicorn.run("webapp.main:app", host=host, port=port, reload=False)
