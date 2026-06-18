from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from src.calendar_tw import MARKET_OPEN, localize_taipei, minutes_after_open, minutes_before_close
from src.market.cost_model import TaiwanStockCostModel
from src.strategies.base import StrategyBase, StrategySignal


@dataclass(frozen=True)
class OpeningRangeBreakoutParams:
    opening_range_minutes: int = 15
    volume_multiplier: float = 1.5
    take_profit_r: float = 2.0
    stop_buffer_bps: float = 10.0
    avoid_close_minutes: int = 10
    max_position_value: float = 100_000


class OpeningRangeBreakoutStrategy(StrategyBase):
    signal_type = "OPENING_RANGE_BREAKOUT"

    def __init__(
        self,
        params: OpeningRangeBreakoutParams | None = None,
        cost_model: TaiwanStockCostModel | None = None,
    ) -> None:
        self.params = params or OpeningRangeBreakoutParams()
        self.cost_model = cost_model or TaiwanStockCostModel()

    def generate(self, intraday: pd.DataFrame, stock_id: str, current_time: datetime) -> StrategySignal:
        current_time = localize_taipei(current_time)
        if intraday.empty:
            return StrategySignal.hold(stock_id, self.signal_type, "no intraday data", current_time)
        if minutes_after_open(current_time) < self.params.opening_range_minutes:
            return StrategySignal.hold(stock_id, self.signal_type, "opening range is not complete", current_time)
        if minutes_before_close(current_time) < self.params.avoid_close_minutes:
            return StrategySignal.hold(stock_id, self.signal_type, "too close to market close for new entry", current_time)

        frame = intraday.copy()
        frame["datetime"] = pd.to_datetime(frame["datetime"])
        frame = frame[frame["datetime"] <= pd.Timestamp(current_time).tz_localize(None)].sort_values("datetime")
        if frame.empty:
            return StrategySignal.hold(stock_id, self.signal_type, "no rows up to current_time", current_time)

        open_start = pd.Timestamp.combine(frame["datetime"].dt.date.iloc[-1], MARKET_OPEN)
        open_end = open_start + pd.Timedelta(minutes=self.params.opening_range_minutes)
        opening = frame[(frame["datetime"] >= open_start) & (frame["datetime"] < open_end)]
        if opening.empty:
            return StrategySignal.hold(stock_id, self.signal_type, "missing opening range rows", current_time)

        latest = frame.iloc[-1]
        range_high = float(opening["price"].max())
        range_low = float(opening["price"].min())
        baseline_volume = float(opening["volume"].mean())
        if latest["price"] <= range_high:
            return StrategySignal.hold(stock_id, self.signal_type, "price has not broken opening range high", current_time)
        if baseline_volume <= 0 or latest["volume"] < baseline_volume * self.params.volume_multiplier:
            return StrategySignal.hold(stock_id, self.signal_type, "breakout volume is insufficient", current_time)

        entry = float(latest["price"])
        stop = round(range_low * (1 - self.params.stop_buffer_bps / 10000), 2)
        risk = entry - stop
        if risk <= 0:
            return StrategySignal.hold(stock_id, self.signal_type, "invalid stop distance", current_time)
        take_profit = round(entry + risk * self.params.take_profit_r, 2)
        expected_edge_bps = ((take_profit - entry) / entry) * 10000
        if not self.cost_model.has_sufficient_edge(expected_edge_bps, entry, 1000, is_day_trade=True):
            return StrategySignal.hold(stock_id, self.signal_type, "expected edge does not clear costs", current_time)
        return StrategySignal(
            stock_id=stock_id,
            side="BUY",
            signal_type=self.signal_type,
            confidence=0.7,
            entry_price=entry,
            stop_loss=stop,
            take_profit=take_profit,
            max_position_value=self.params.max_position_value,
            reason=f"price {entry:.2f} broke opening range high {range_high:.2f} with volume expansion",
            invalid_reason="",
            created_at=current_time,
        )
