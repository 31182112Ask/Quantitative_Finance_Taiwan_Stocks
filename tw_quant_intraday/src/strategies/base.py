from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Literal

Side = Literal["BUY", "SELL", "HOLD", "CLOSE"]
SignalType = Literal[
    "INTRADAY_MOMENTUM",
    "OPENING_RANGE_BREAKOUT",
    "VWAP_REVERSION",
    "T_PLUS_ONE_SWING",
    "RISK_EXIT",
]


@dataclass(frozen=True)
class StrategySignal:
    stock_id: str
    side: Side
    signal_type: SignalType
    confidence: float
    entry_price: float | None
    stop_loss: float | None
    take_profit: float | None
    max_position_value: float | None
    reason: str
    invalid_reason: str
    created_at: datetime
    stock_name: str = ""

    def to_dict(self) -> dict:
        result = asdict(self)
        result["created_at"] = self.created_at.isoformat()
        return result

    @classmethod
    def hold(cls, stock_id: str, signal_type: SignalType, reason: str, created_at: datetime) -> "StrategySignal":
        return cls(
            stock_id=stock_id,
            side="HOLD",
            signal_type=signal_type,
            confidence=0.0,
            entry_price=None,
            stop_loss=None,
            take_profit=None,
            max_position_value=None,
            reason=reason,
            invalid_reason=reason,
            created_at=created_at,
        )


class StrategyBase:
    signal_type: SignalType

    def generate(self, *args, **kwargs) -> StrategySignal:
        raise NotImplementedError
