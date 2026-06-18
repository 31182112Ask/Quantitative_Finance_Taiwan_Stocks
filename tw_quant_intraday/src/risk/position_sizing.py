from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PositionSizeResult:
    quantity: int
    amount: float
    risk_amount: float


def shares_by_risk(
    equity: float,
    entry_price: float,
    stop_loss: float,
    max_trade_loss_pct: float,
    max_position_pct: float,
    lot_size: int = 1000,
) -> PositionSizeResult:
    if equity <= 0 or entry_price <= 0 or stop_loss <= 0:
        raise ValueError("equity, entry_price, and stop_loss must be positive")
    risk_per_share = max(entry_price - stop_loss, 0)
    if risk_per_share <= 0:
        return PositionSizeResult(quantity=0, amount=0, risk_amount=0)
    risk_budget = equity * max_trade_loss_pct
    position_budget = equity * max_position_pct
    quantity_by_risk = int(risk_budget // risk_per_share)
    quantity_by_position = int(position_budget // entry_price)
    quantity = min(quantity_by_risk, quantity_by_position)
    quantity = (quantity // lot_size) * lot_size if lot_size > 1 else quantity
    amount = quantity * entry_price
    return PositionSizeResult(quantity=quantity, amount=amount, risk_amount=quantity * risk_per_share)
