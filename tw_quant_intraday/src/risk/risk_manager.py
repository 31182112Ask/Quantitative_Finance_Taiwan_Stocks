from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from src.calendar_tw import is_trading_time, minutes_after_open, minutes_before_close
from src.risk.position_sizing import PositionSizeResult, shares_by_risk


@dataclass(frozen=True)
class RiskLimits:
    max_position_pct_per_stock: float = 0.10
    max_daily_turnover_pct: float = 0.30
    max_daily_loss_pct: float = 0.02
    max_trade_loss_pct: float = 0.008
    max_trades_per_day: int = 6
    max_consecutive_losses: int = 3
    min_avg_turnover_20d: float = 50_000_000
    order_lot_size: int = 1
    avoid_open_minutes: int = 5
    avoid_close_minutes: int = 10
    require_manual_confirm: bool = True

    @classmethod
    def from_mapping(cls, data: dict) -> "RiskLimits":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class RiskState:
    equity: float
    daily_turnover: float = 0.0
    daily_pnl: float = 0.0
    trades_today: int = 0
    consecutive_losses: int = 0
    positions: dict[str, float] = field(default_factory=dict)
    data_delay_seconds: int = 0
    system_error: bool = False


@dataclass(frozen=True)
class RiskDecision:
    approved: bool
    reason: str
    size: PositionSizeResult
    notes: list[str]


class RiskManager:
    def __init__(self, limits: RiskLimits | None = None) -> None:
        self.limits = limits or RiskLimits()

    def evaluate_entry(
        self,
        *,
        stock_id: str,
        side: str,
        entry_price: float,
        stop_loss: float,
        current_time: datetime,
        state: RiskState,
        avg_turnover_20d: float,
        data_is_fresh: bool,
        expected_amount: float | None = None,
        previous_close: float | None = None,
    ) -> RiskDecision:
        empty_size = PositionSizeResult(quantity=0, amount=0, risk_amount=0)
        notes: list[str] = []
        if side not in {"BUY", "SELL", "CLOSE"}:
            return RiskDecision(False, "unsupported side", empty_size, notes)
        if side == "SELL" and stock_id not in state.positions:
            return RiskDecision(False, "sell signal without an existing position is blocked", empty_size, notes)
        if state.system_error:
            return RiskDecision(False, "system error kill switch is active", empty_size, notes)
        if not data_is_fresh or state.data_delay_seconds > 60:
            return RiskDecision(False, "market data is stale or missing", empty_size, notes)
        if not is_trading_time(current_time):
            return RiskDecision(False, "outside Taiwan regular trading session", empty_size, notes)
        if minutes_after_open(current_time) < self.limits.avoid_open_minutes:
            return RiskDecision(False, "inside open-avoidance window", empty_size, notes)
        if minutes_before_close(current_time) < self.limits.avoid_close_minutes:
            return RiskDecision(False, "inside close-avoidance window", empty_size, notes)
        if state.daily_pnl <= -(state.equity * self.limits.max_daily_loss_pct):
            return RiskDecision(False, "daily loss limit reached", empty_size, notes)
        if state.trades_today >= self.limits.max_trades_per_day:
            return RiskDecision(False, "daily trade count limit reached", empty_size, notes)
        if state.consecutive_losses >= self.limits.max_consecutive_losses:
            return RiskDecision(False, "consecutive loss kill switch is active", empty_size, notes)
        if avg_turnover_20d < self.limits.min_avg_turnover_20d:
            return RiskDecision(False, "liquidity below minimum average turnover", empty_size, notes)
        if previous_close and entry_price >= previous_close * 1.097:
            return RiskDecision(False, "price is too close to limit up", empty_size, notes)

        size = shares_by_risk(
            state.equity,
            entry_price,
            stop_loss,
            self.limits.max_trade_loss_pct,
            self.limits.max_position_pct_per_stock,
            self.limits.order_lot_size,
        )
        amount = expected_amount if expected_amount is not None else size.amount
        if size.quantity <= 0:
            return RiskDecision(False, "position size is zero after risk constraints", size, notes)
        if state.daily_turnover + amount > state.equity * self.limits.max_daily_turnover_pct:
            return RiskDecision(False, "daily turnover limit would be exceeded", size, notes)
        if self.limits.require_manual_confirm:
            notes.append("manual confirmation required before any broker-side action")
        return RiskDecision(True, "approved", size, notes)
