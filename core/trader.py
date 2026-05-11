"""Order placement via ccxt. Supports optional stop-loss / take-profit as separate orders."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import ccxt


@dataclass
class TradeResult:
    ok: bool
    message: str
    order: Optional[dict] = None
    sl_order: Optional[dict] = None
    tp_order: Optional[dict] = None

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "message": self.message,
            "order_id": (self.order or {}).get("id"),
            "sl_order_id": (self.sl_order or {}).get("id"),
            "tp_order_id": (self.tp_order or {}).get("id"),
        }


def _build_exchange(
    exchange_name: str,
    api_key: str,
    api_secret: str,
    testnet: bool,
) -> ccxt.Exchange:
    ex_cls = getattr(ccxt, exchange_name.lower(), None)
    if ex_cls is None:
        raise ValueError(f"Unknown exchange: {exchange_name}")
    ex = ex_cls(
        {
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
            "options": {"defaultType": "spot"},
        }
    )
    if testnet:
        try:
            ex.set_sandbox_mode(True)
        except Exception:
            # Not all exchanges support sandbox; caller should be warned in logs.
            pass
    return ex


def place_order(
    *,
    exchange: str,
    api_key: str,
    api_secret: str,
    testnet: bool,
    symbol: str,
    side: str,               # "buy" or "sell"
    amount: float,           # base-asset quantity
    order_type: str = "market",
    price: Optional[float] = None,
    stop_loss_pct: Optional[float] = None,
    take_profit_pct: Optional[float] = None,
) -> TradeResult:
    side = side.lower()
    if side not in ("buy", "sell"):
        return TradeResult(ok=False, message=f"Invalid side: {side}")
    if amount <= 0:
        return TradeResult(ok=False, message="Amount must be > 0")

    try:
        ex = _build_exchange(exchange, api_key, api_secret, testnet)
        ex.load_markets()

        params: dict = {}
        if order_type == "market":
            order = ex.create_order(symbol, "market", side, amount, None, params)
        else:
            if price is None:
                return TradeResult(ok=False, message="Limit order requires a price")
            order = ex.create_order(symbol, "limit", side, amount, price, params)

        fill_price = float(order.get("average") or order.get("price") or price or 0.0)
        if not fill_price:
            ticker = ex.fetch_ticker(symbol)
            fill_price = float(ticker.get("last") or 0.0)

        opposite = "sell" if side == "buy" else "buy"
        sl_order = None
        tp_order = None

        if stop_loss_pct and fill_price:
            sl_price = fill_price * (1 - stop_loss_pct / 100) if side == "buy" else fill_price * (1 + stop_loss_pct / 100)
            try:
                sl_order = ex.create_order(
                    symbol, "stop_market", opposite, amount, None,
                    {"stopPrice": ex.price_to_precision(symbol, sl_price)},
                )
            except Exception as e:  # noqa: BLE001
                sl_order = {"error": str(e)}

        if take_profit_pct and fill_price:
            tp_price = fill_price * (1 + take_profit_pct / 100) if side == "buy" else fill_price * (1 - take_profit_pct / 100)
            try:
                tp_order = ex.create_order(
                    symbol, "take_profit_market", opposite, amount, None,
                    {"stopPrice": ex.price_to_precision(symbol, tp_price)},
                )
            except Exception as e:  # noqa: BLE001
                tp_order = {"error": str(e)}

        return TradeResult(
            ok=True,
            message=f"{side.upper()} {amount} {symbol} @ ~{fill_price}",
            order=order,
            sl_order=sl_order,
            tp_order=tp_order,
        )
    except Exception as e:  # noqa: BLE001
        return TradeResult(ok=False, message=f"{type(e).__name__}: {e}")
