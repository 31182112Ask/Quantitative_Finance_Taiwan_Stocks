from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from src.calendar_tw import localize_taipei
from src.features.technical import moving_average
from src.market.cost_model import TaiwanStockCostModel
from src.strategies.base import StrategyBase, StrategySignal


@dataclass(frozen=True)
class TPlusOneSwingParams:
    ma_fast: int = 20
    ma_slow: int = 60
    volume_lookback: int = 5
    breakout_lookback: int = 20
    stop_loss_pct: float = 0.035
    take_profit_pct: float = 0.07
    max_position_value: float = 100_000


class TPlusOneSwingStrategy(StrategyBase):
    signal_type = "T_PLUS_ONE_SWING"

    def __init__(
        self,
        params: TPlusOneSwingParams | None = None,
        cost_model: TaiwanStockCostModel | None = None,
    ) -> None:
        self.params = params or TPlusOneSwingParams()
        self.cost_model = cost_model or TaiwanStockCostModel()

    def generate(self, daily: pd.DataFrame, stock_id: str, current_time: datetime) -> StrategySignal:
        current_time = localize_taipei(current_time)
        stock = daily[daily["stock_id"].astype(str) == str(stock_id)].copy()
        if len(stock) < self.params.ma_slow + 1:
            return StrategySignal.hold(stock_id, self.signal_type, "insufficient daily history", current_time)
        stock = stock.sort_values("date")
        stock["ma_fast"] = moving_average(stock["close"], self.params.ma_fast)
        stock["ma_slow"] = moving_average(stock["close"], self.params.ma_slow)
        stock["prior_breakout_high"] = stock["high"].shift(1).rolling(self.params.breakout_lookback).max()
        latest = stock.iloc[-1]
        prev_volume_base = stock["volume"].shift(self.params.volume_lookback).rolling(20, min_periods=5).mean().iloc[-1]
        recent_volume = stock["volume"].tail(self.params.volume_lookback).mean()

        if pd.isna(latest["ma_fast"]) or pd.isna(latest["ma_slow"]) or pd.isna(latest["prior_breakout_high"]):
            return StrategySignal.hold(stock_id, self.signal_type, "insufficient indicator history", current_time)
        if latest["close"] <= latest["ma_fast"] or latest["close"] <= latest["ma_slow"]:
            return StrategySignal.hold(stock_id, self.signal_type, "close is not above 20d and 60d moving averages", current_time)
        if recent_volume <= prev_volume_base:
            return StrategySignal.hold(stock_id, self.signal_type, "recent volume structure is not stronger than baseline", current_time)
        if latest["close"] <= latest["prior_breakout_high"]:
            return StrategySignal.hold(stock_id, self.signal_type, "close has not broken prior range", current_time)

        entry = float(latest["close"])
        stop = round(entry * (1 - self.params.stop_loss_pct), 2)
        take_profit = round(entry * (1 + self.params.take_profit_pct), 2)
        expected_edge_bps = self.params.take_profit_pct * 10000
        if not self.cost_model.has_sufficient_edge(expected_edge_bps, entry, 1000, is_day_trade=False):
            return StrategySignal.hold(stock_id, self.signal_type, "expected edge does not clear costs", current_time)
        return StrategySignal(
            stock_id=stock_id,
            stock_name=str(latest.get("stock_name", "")),
            side="BUY",
            signal_type=self.signal_type,
            confidence=0.65,
            entry_price=entry,
            stop_loss=stop,
            take_profit=take_profit,
            max_position_value=self.params.max_position_value,
            reason="close above 20d/60d averages with stronger 5d volume and range breakout",
            invalid_reason="",
            created_at=current_time,
        )
