from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from src.backtest.metrics import performance_metrics
from src.market.cost_model import TaiwanStockCostModel
from src.strategies.t_plus_one_swing import TPlusOneSwingStrategy


@dataclass(frozen=True)
class BacktestResult:
    trades: pd.DataFrame
    equity_curve: pd.DataFrame
    metrics: dict[str, float]


class SimpleDailyBacktester:
    def __init__(self, initial_cash: float = 1_000_000, cost_model: TaiwanStockCostModel | None = None) -> None:
        self.initial_cash = initial_cash
        self.cost_model = cost_model or TaiwanStockCostModel()

    def run_t_plus_one(self, daily: pd.DataFrame, strategy: TPlusOneSwingStrategy | None = None) -> BacktestResult:
        strategy = strategy or TPlusOneSwingStrategy(cost_model=self.cost_model)
        cash = self.initial_cash
        equity_rows: list[dict] = []
        trade_rows: list[dict] = []
        for stock_id, stock in daily.groupby("stock_id"):
            stock = stock.sort_values("date").reset_index(drop=True)
            for idx in range(60, len(stock) - 1):
                window = stock.iloc[: idx + 1]
                now = pd.Timestamp(window.iloc[-1]["date"]).to_pydatetime()
                signal = strategy.generate(window, str(stock_id), now)
                if signal.side != "BUY" or signal.entry_price is None or signal.stop_loss is None:
                    equity_rows.append({"date": window.iloc[-1]["date"], "equity": cash})
                    continue
                entry_row = stock.iloc[idx + 1]
                exit_idx = min(idx + 5, len(stock) - 1)
                exit_window = stock.iloc[idx + 1 : exit_idx + 1]
                exit_row = exit_window.iloc[-1]
                for _, row in exit_window.iterrows():
                    if row["low"] <= signal.stop_loss:
                        exit_row = row
                        break
                    if signal.take_profit is not None and row["high"] >= signal.take_profit:
                        exit_row = row
                        break
                entry = float(entry_row["open"])
                exit_price = float(exit_row["close"])
                quantity = int(min(signal.max_position_value or 100_000, cash * 0.1) // entry)
                quantity = (quantity // 1000) * 1000
                if quantity <= 0:
                    equity_rows.append({"date": window.iloc[-1]["date"], "equity": cash})
                    continue
                buy_cost = self.cost_model.estimate("BUY", entry, quantity)
                sell_cost = self.cost_model.estimate("SELL", exit_price, quantity)
                pnl = (exit_price - entry) * quantity - buy_cost.total - sell_cost.total
                cash += pnl
                holding_minutes = max((pd.Timestamp(exit_row["date"]) - pd.Timestamp(entry_row["date"])).days, 1) * 270
                trade_rows.append({
                    "stock_id": stock_id,
                    "entry_date": entry_row["date"],
                    "exit_date": exit_row["date"],
                    "entry_price": entry,
                    "exit_price": exit_price,
                    "quantity": quantity,
                    "notional": entry * quantity + exit_price * quantity,
                    "cost": buy_cost.total + sell_cost.total,
                    "slippage": buy_cost.slippage + sell_cost.slippage,
                    "pnl": pnl,
                    "holding_minutes": holding_minutes,
                    "strategy": "T_PLUS_ONE_SWING",
                })
                equity_rows.append({"date": exit_row["date"], "equity": cash})
        trades = pd.DataFrame(trade_rows)
        equity_curve = pd.DataFrame(equity_rows).drop_duplicates("date", keep="last")
        if equity_curve.empty:
            equity_curve = pd.DataFrame([{"date": datetime.now().date(), "equity": cash}])
        metrics = performance_metrics(equity_curve, trades, initial_cash=self.initial_cash)
        return BacktestResult(trades=trades, equity_curve=equity_curve, metrics=metrics)
