from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class RunMode(StrEnum):
    BACKTEST = "BACKTEST"
    PAPER = "PAPER"
    LIVE = "LIVE"


class Side(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    UNKNOWN = "UNKNOWN"


class DecisionAction(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass(slots=True, frozen=True)
class Tick:
    ts_ms: int
    price: float
    size: int
    side: Side = Side.UNKNOWN
    bid: float | None = None
    ask: float | None = None


@dataclass(slots=True)
class Bar:
    time: int
    open: float
    high: float
    low: float
    close: float
    volume: int
    turnover: float
    trades: int

    @property
    def vwap(self) -> float:
        return self.turnover / self.volume if self.volume else self.close

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["vwap"] = round(self.vwap, 4)
        return payload


@dataclass(slots=True)
class Decision:
    time: int
    action: DecisionAction
    reason: str
    score: int
    entry: float | None
    stop: float | None
    take_profit: float | None
    fast_ema: float
    slow_ema: float
    vwap: float

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["action"] = self.action.value
        return payload


@dataclass(slots=True)
class SignalMarker:
    time: int
    action: DecisionAction
    price: float
    text: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "time": self.time,
            "action": self.action.value,
            "price": round(self.price, 4),
            "text": self.text,
        }


@dataclass(slots=True)
class AccountState:
    starting_equity: float = 1_000_000.0
    cash: float = 1_000_000.0
    position_qty: int = 0
    avg_price: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    fees: float = 0.0
    equity: float = 1_000_000.0
    peak_equity: float = 1_000_000.0
    max_drawdown: float = 0.0
    trades: int = 0

    def mark(self, last_price: float) -> None:
        self.unrealized_pnl = (
            (last_price - self.avg_price) * self.position_qty
            if self.position_qty
            else 0.0
        )
        self.equity = self.cash + self.position_qty * last_price
        self.peak_equity = max(self.peak_equity, self.equity)
        if self.peak_equity > 0:
            drawdown = (self.peak_equity - self.equity) / self.peak_equity
            self.max_drawdown = max(self.max_drawdown, drawdown)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for key, value in payload.items():
            if isinstance(value, float):
                payload[key] = round(value, 4)
        return payload
