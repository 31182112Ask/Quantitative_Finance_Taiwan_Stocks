from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.market.cost_model import TaiwanStockCostModel
from src.paper.paper_account import PaperAccount
from src.strategies.base import StrategySignal


class PaperEngine:
    def __init__(self, account: PaperAccount | None = None, cost_model: TaiwanStockCostModel | None = None) -> None:
        self.account = account or PaperAccount()
        self.cost_model = cost_model or TaiwanStockCostModel()
        self.trades: list[dict] = []
        self.equity_curve: list[dict] = []

    def apply_signal(self, signal: StrategySignal, quantity: int) -> None:
        if signal.side != "BUY" or signal.entry_price is None or quantity <= 0:
            return
        cost = self.cost_model.estimate("BUY", signal.entry_price, quantity)
        self.account.buy(signal.stock_id, signal.entry_price, quantity, cost.total)
        self.trades.append({
            "stock_id": signal.stock_id,
            "side": "BUY",
            "price": signal.entry_price,
            "quantity": quantity,
            "cost": cost.total,
            "strategy": signal.signal_type,
            "created_at": signal.created_at.isoformat(),
        })

    def mark_equity(self, date: str, market_prices: dict[str, float]) -> float:
        equity = self.account.cash
        for stock_id, position in self.account.positions.items():
            equity += position.quantity * market_prices.get(stock_id, position.avg_price)
        self.equity_curve.append({"date": date, "equity": equity})
        return equity

    def write_reports(self, report_dir: str | Path) -> None:
        path = Path(report_dir)
        path.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(self.trades).to_csv(path / "trades.csv", index=False)
        pd.DataFrame(self.equity_curve).to_csv(path / "equity_curve.csv", index=False)
        latest_equity = self.equity_curve[-1]["equity"] if self.equity_curve else self.account.cash
        (path / "daily_report.md").write_text(
            f"# Paper Trading Daily Report\n\nLatest equity: {latest_equity:.2f}\n\n"
            "No broker connection or automatic order submission is performed.\n",
            encoding="utf-8",
        )
        (path / "performance.md").write_text(
            "# Paper Trading Performance\n\n"
            f"- latest_equity: {latest_equity:.2f}\n"
            f"- realized_pnl: {self.account.realized_pnl:.2f}\n"
            f"- trade_count: {len(self.trades)}\n"
            "\nNo broker connection or automatic order submission is performed.\n",
            encoding="utf-8",
        )
