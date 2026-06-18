from __future__ import annotations

from datetime import datetime

import pandas as pd

from src.features.technical import returns, vwap
from src.market.cost_model import TaiwanStockCostModel
from src.strategies.base import StrategyBase, StrategySignal


class IntradayMomentumStrategy(StrategyBase):
    signal_type = "INTRADAY_MOMENTUM"

    def __init__(self, cost_model: TaiwanStockCostModel | None = None) -> None:
        self.cost_model = cost_model or TaiwanStockCostModel()

    def generate(self, intraday: pd.DataFrame, stock_id: str, current_time: datetime) -> StrategySignal:
        if len(intraday) < 20:
            return StrategySignal.hold(stock_id, self.signal_type, "insufficient intraday rows", current_time)
        frame = intraday.copy().sort_values("datetime")
        frame["vwap"] = vwap(frame)
        frame["ret5"] = returns(frame["price"], 5)
        latest = frame.iloc[-1]
        if latest["price"] <= latest["vwap"] or latest["ret5"] <= 0:
            return StrategySignal.hold(stock_id, self.signal_type, "price is not above VWAP with positive 5-row return", current_time)
        entry = float(latest["price"])
        stop = round(entry * 0.99, 2)
        take_profit = round(entry * 1.025, 2)
        if not self.cost_model.has_sufficient_edge(250, entry, 1000, is_day_trade=True):
            return StrategySignal.hold(stock_id, self.signal_type, "expected edge does not clear costs", current_time)
        return StrategySignal(stock_id, "BUY", self.signal_type, 0.55, entry, stop, take_profit, 100_000, "intraday momentum above VWAP", "", current_time)
