"""Market analysis: fetch OHLCV via ccxt, compute simple indicators, emit a signal."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import ccxt
import numpy as np
import pandas as pd

Signal = Literal["BUY", "SELL", "HOLD"]


@dataclass
class AnalysisResult:
    symbol: str
    timeframe: str
    last_price: float
    rsi: float
    ema_fast: float
    ema_slow: float
    signal: Signal
    reason: str

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "last_price": round(self.last_price, 6),
            "rsi": round(self.rsi, 2),
            "ema_fast": round(self.ema_fast, 6),
            "ema_slow": round(self.ema_slow, 6),
            "signal": self.signal,
            "reason": self.reason,
        }


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def _fetch_ohlcv(exchange_name: str, symbol: str, timeframe: str, limit: int = 200) -> pd.DataFrame:
    ex_cls = getattr(ccxt, exchange_name.lower(), None)
    if ex_cls is None:
        raise ValueError(f"Unknown exchange: {exchange_name}")
    ex = ex_cls({"enableRateLimit": True})
    ohlcv = ex.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=["ts", "open", "high", "low", "close", "volume"])
    df["ts"] = pd.to_datetime(df["ts"], unit="ms")
    return df


def analyze(
    exchange: str,
    symbol: str,
    timeframe: str,
    strategy: str = "rsi_ema",
    rsi_period: int = 14,
    ema_fast: int = 9,
    ema_slow: int = 21,
) -> AnalysisResult:
    """Run a simple RSI + EMA-cross analysis and return a trading signal."""
    df = _fetch_ohlcv(exchange, symbol, timeframe)
    if len(df) < max(rsi_period, ema_slow) + 2:
        raise ValueError("Not enough candles returned to analyze.")

    close = df["close"]
    df["rsi"] = _rsi(close, rsi_period)
    df["ema_f"] = close.ewm(span=ema_fast, adjust=False).mean()
    df["ema_s"] = close.ewm(span=ema_slow, adjust=False).mean()

    last = df.iloc[-1]
    prev = df.iloc[-2]

    signal: Signal = "HOLD"
    reasons: list[str] = []

    crossed_up = prev["ema_f"] <= prev["ema_s"] and last["ema_f"] > last["ema_s"]
    crossed_down = prev["ema_f"] >= prev["ema_s"] and last["ema_f"] < last["ema_s"]

    if strategy in ("rsi_ema", "ema_cross"):
        if crossed_up:
            reasons.append(f"EMA{ema_fast} crossed above EMA{ema_slow}")
            signal = "BUY"
        elif crossed_down:
            reasons.append(f"EMA{ema_fast} crossed below EMA{ema_slow}")
            signal = "SELL"

    if strategy in ("rsi_ema", "rsi"):
        if last["rsi"] < 30 and signal != "SELL":
            reasons.append(f"RSI {last['rsi']:.1f} < 30 (oversold)")
            signal = "BUY"
        elif last["rsi"] > 70 and signal != "BUY":
            reasons.append(f"RSI {last['rsi']:.1f} > 70 (overbought)")
            signal = "SELL"

    if not reasons:
        reasons.append("No trigger; trend/momentum neutral.")

    return AnalysisResult(
        symbol=symbol,
        timeframe=timeframe,
        last_price=float(last["close"]),
        rsi=float(last["rsi"]),
        ema_fast=float(last["ema_f"]),
        ema_slow=float(last["ema_s"]),
        signal=signal,
        reason="; ".join(reasons),
    )
