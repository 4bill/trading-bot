"""Market analysis: fetch OHLCV via ccxt, compute simple indicators, emit a signal.

Pure-Python implementation (no pandas / numpy) so the container stays small and
installs quickly on free hosts.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Literal

import ccxt

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


def _ema_series(values: Iterable[float], span: int) -> List[float]:
    """Exponential moving average, same convention as pandas ewm(span=span, adjust=False)."""
    alpha = 2 / (span + 1)
    out: List[float] = []
    prev: float | None = None
    for v in values:
        if prev is None:
            prev = float(v)
        else:
            prev = alpha * float(v) + (1 - alpha) * prev
        out.append(prev)
    return out


def _rsi_series(values: List[float], period: int = 14) -> List[float]:
    """Wilder's RSI using EWM-like smoothing; matches pandas version for period>=2."""
    if len(values) < 2:
        return [50.0] * len(values)

    alpha = 1 / period
    gains_ema: float | None = None
    losses_ema: float | None = None
    rsi: List[float] = [50.0]  # first value: neutral

    for i in range(1, len(values)):
        change = values[i] - values[i - 1]
        gain = max(change, 0.0)
        loss = max(-change, 0.0)
        if gains_ema is None:
            gains_ema = gain
            losses_ema = loss
        else:
            gains_ema = alpha * gain + (1 - alpha) * gains_ema
            losses_ema = alpha * loss + (1 - alpha) * losses_ema
        if losses_ema == 0:
            rsi.append(100.0 if gains_ema and gains_ema > 0 else 50.0)
        else:
            rs = (gains_ema or 0) / losses_ema
            rsi.append(100 - (100 / (1 + rs)))
    return rsi


def _fetch_closes(exchange_name: str, symbol: str, timeframe: str, limit: int = 200) -> List[float]:
    ex_cls = getattr(ccxt, exchange_name.lower(), None)
    if ex_cls is None:
        raise ValueError(f"Unknown exchange: {exchange_name}")
    ex = ex_cls({"enableRateLimit": True})
    ohlcv = ex.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    # rows are [ts, open, high, low, close, volume]
    return [float(row[4]) for row in ohlcv]


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
    closes = _fetch_closes(exchange, symbol, timeframe)
    if len(closes) < max(rsi_period, ema_slow) + 2:
        raise ValueError("Not enough candles returned to analyze.")

    rsi_vals = _rsi_series(closes, rsi_period)
    ema_f_vals = _ema_series(closes, ema_fast)
    ema_s_vals = _ema_series(closes, ema_slow)

    last_rsi = rsi_vals[-1]
    last_ema_f = ema_f_vals[-1]
    last_ema_s = ema_s_vals[-1]
    prev_ema_f = ema_f_vals[-2]
    prev_ema_s = ema_s_vals[-2]
    last_close = closes[-1]

    signal: Signal = "HOLD"
    reasons: List[str] = []

    crossed_up = prev_ema_f <= prev_ema_s and last_ema_f > last_ema_s
    crossed_down = prev_ema_f >= prev_ema_s and last_ema_f < last_ema_s

    if strategy in ("rsi_ema", "ema_cross"):
        if crossed_up:
            reasons.append(f"EMA{ema_fast} crossed above EMA{ema_slow}")
            signal = "BUY"
        elif crossed_down:
            reasons.append(f"EMA{ema_fast} crossed below EMA{ema_slow}")
            signal = "SELL"

    if strategy in ("rsi_ema", "rsi"):
        if last_rsi < 30 and signal != "SELL":
            reasons.append(f"RSI {last_rsi:.1f} < 30 (oversold)")
            signal = "BUY"
        elif last_rsi > 70 and signal != "BUY":
            reasons.append(f"RSI {last_rsi:.1f} > 70 (overbought)")
            signal = "SELL"

    if not reasons:
        reasons.append("No trigger; trend/momentum neutral.")

    return AnalysisResult(
        symbol=symbol,
        timeframe=timeframe,
        last_price=last_close,
        rsi=last_rsi,
        ema_fast=last_ema_f,
        ema_slow=last_ema_s,
        signal=signal,
        reason="; ".join(reasons),
    )
