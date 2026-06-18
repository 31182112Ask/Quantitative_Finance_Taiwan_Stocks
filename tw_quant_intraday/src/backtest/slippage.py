from __future__ import annotations


def apply_slippage(price: float, side: str, slippage_bps: float) -> float:
    if price <= 0:
        raise ValueError("price must be positive")
    adjustment = slippage_bps / 10000
    if side == "BUY":
        return price * (1 + adjustment)
    if side in {"SELL", "CLOSE"}:
        return price * (1 - adjustment)
    raise ValueError("side must be BUY, SELL, or CLOSE")
