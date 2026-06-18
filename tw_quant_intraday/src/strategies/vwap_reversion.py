from __future__ import annotations

from datetime import datetime

import pandas as pd

from src.features.technical import vwap
from src.market.cost_model import TaiwanStockCostModel
from src.strategies.base import StrategyBase, StrategySignal


class VwapReversionStrategy(StrategyBase):
    signal_type = "VWAP_REVERSION"

    def __init__(self, cost_model: TaiwanStockCostModel | None = None) -> None:
        self.cost_model = cost_model or TaiwanStockCostModel()

    def generate(self, intraday: pd.DataFrame, stock_id: str, current_time: datetime) -> StrategySignal:
        if len(intraday) < 20:
            return StrategySignal.hold(stock_id, self.signal_type, "insufficient intraday rows", current_time)
        frame = intraday.copy().sort_values("datetime")
        frame["vwap"] = vwap(frame)
        latest = frame.iloc[-1]
        deviation = (latest["price"] - latest["vwap"]) / latest["vwap"]
        if deviation >= -0.015:
            return StrategySignal.hold(stock_id, self.signal_type, "price is not sufficiently below VWAP", current_time)
        entry = float(latest["price"])
        stop = round(entry * 0.985, 2)
        take_profit = round(float(latest["vwap"]), 2)
        expected_edge_bps = ((take_profit - entry) / entry) * 10000
        if not self.cost_model.has_sufficient_edge(expected_edge_bps, entry, 1000, is_day_trade=True):
            return StrategySignal.hold(stock_id, self.signal_type, "expected edge does not clear costs", current_time)
        return StrategySignal(stock_id, "BUY", self.signal_type, 0.5, entry, stop, take_profit, 80_000, "VWAP reversion candidate", "", current_time)
