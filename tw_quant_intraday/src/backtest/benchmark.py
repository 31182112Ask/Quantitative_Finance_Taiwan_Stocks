from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from src.backtest.metrics import performance_metrics
from src.market.cost_model import TaiwanStockCostModel
from src.strategies.t_plus_one_swing import TPlusOneSwingParams, TPlusOneSwingStrategy


@dataclass(frozen=True)
class BenchmarkConfig:
    start_date: date
    end_date: date
    initial_cash: float = 10_000
    lot_size: int = 1
    max_holding_days: int = 5
    allow_mock: bool = False


@dataclass(frozen=True)
class BenchmarkResult:
    trades: pd.DataFrame
    equity_curve: pd.DataFrame
    metrics: dict[str, float]
    summary: dict[str, float | int | str]


class RecommendedStrategyBenchmark:
    def __init__(self, cost_model: TaiwanStockCostModel | None = None) -> None:
        self.cost_model = cost_model or TaiwanStockCostModel()

    def run(self, daily: pd.DataFrame, config: BenchmarkConfig) -> BenchmarkResult:
        frame = daily.copy()
        if frame.empty:
            raise ValueError("benchmark requires non-empty daily data")
        if not config.allow_mock and frame["source"].astype(str).str.contains("mock", case=False, na=False).any():
            raise ValueError("benchmark refuses mock data unless allow_mock=True")

        frame["date"] = pd.to_datetime(frame["date"])
        frame = frame.sort_values(["date", "stock_id"]).reset_index(drop=True)
        start_ts = pd.Timestamp(config.start_date)
        end_ts = pd.Timestamp(config.end_date)
        period_rows = frame[(frame["date"] >= start_ts) & (frame["date"] <= end_ts)]
        if period_rows.empty:
            raise ValueError(f"no daily rows inside benchmark window {config.start_date} to {config.end_date}")

        cash = float(config.initial_cash)
        open_positions: list[dict] = []
        trades: list[dict] = []
        equity_rows: list[dict] = []
        strategy = TPlusOneSwingStrategy(
            params=TPlusOneSwingParams(max_position_value=config.initial_cash),
            cost_model=self.cost_model,
        )
        all_dates = sorted(period_rows["date"].drop_duplicates())
        scheduled_entries: list[dict] = []

        for stock_id, stock in frame.groupby("stock_id"):
            stock = stock.sort_values("date").reset_index(drop=True)
            for idx in range(len(stock) - 1):
                signal_day = stock.iloc[idx]["date"]
                if signal_day < start_ts or signal_day > end_ts:
                    continue
                window = stock.iloc[: idx + 1]
                signal = strategy.generate(window, str(stock_id), signal_day.to_pydatetime())
                if signal.side != "BUY" or signal.entry_price is None or signal.stop_loss is None:
                    continue
                entry_row = stock.iloc[idx + 1]
                if entry_row["date"] > end_ts:
                    continue
                scheduled_entries.append(
                    {
                        "stock_id": str(stock_id),
                        "signal_date": signal_day,
                        "entry_date": entry_row["date"],
                        "entry_price": float(entry_row["open"]),
                        "stop_loss": float(signal.stop_loss),
                        "take_profit": float(signal.take_profit) if signal.take_profit is not None else None,
                        "strategy": signal.signal_type,
                        "reason": signal.reason,
                    }
                )

        scheduled_entries.sort(key=lambda row: (row["entry_date"], row["stock_id"]))
        entries_by_date: dict[pd.Timestamp, list[dict]] = {}
        for entry in scheduled_entries:
            entries_by_date.setdefault(entry["entry_date"], []).append(entry)

        for current_date in all_dates:
            day_frame = frame[frame["date"] == current_date]
            remaining_positions: list[dict] = []
            for position in open_positions:
                row = day_frame[day_frame["stock_id"].astype(str) == position["stock_id"]]
                if row.empty:
                    remaining_positions.append(position)
                    continue
                row = row.iloc[0]
                exit_price = None
                exit_reason = ""
                if float(row["low"]) <= position["stop_loss"]:
                    exit_price = position["stop_loss"]
                    exit_reason = "stop_loss"
                elif position["take_profit"] is not None and float(row["high"]) >= position["take_profit"]:
                    exit_price = position["take_profit"]
                    exit_reason = "take_profit"
                elif (current_date - position["entry_date"]).days >= config.max_holding_days:
                    exit_price = float(row["close"])
                    exit_reason = "max_holding_days"
                elif current_date == end_ts or current_date == all_dates[-1]:
                    exit_price = float(row["close"])
                    exit_reason = "period_end_mark_to_market"

                if exit_price is None:
                    remaining_positions.append(position)
                    continue

                sell_cost = self.cost_model.estimate("SELL", exit_price, position["quantity"])
                pnl = (exit_price - position["entry_price"]) * position["quantity"] - position["buy_cost"] - sell_cost.total
                cash += exit_price * position["quantity"] - sell_cost.total
                trades.append(
                    {
                        "stock_id": position["stock_id"],
                        "signal_date": position["signal_date"].date().isoformat(),
                        "entry_date": position["entry_date"].date().isoformat(),
                        "exit_date": current_date.date().isoformat(),
                        "entry_price": position["entry_price"],
                        "exit_price": exit_price,
                        "quantity": position["quantity"],
                        "notional": position["entry_price"] * position["quantity"] + exit_price * position["quantity"],
                        "cost": position["buy_cost"] + sell_cost.total,
                        "slippage": position["buy_slippage"] + sell_cost.slippage,
                        "pnl": pnl,
                        "holding_minutes": max((current_date - position["entry_date"]).days, 1) * 270,
                        "strategy": position["strategy"],
                        "exit_reason": exit_reason,
                    }
                )
            open_positions = remaining_positions

            for entry in entries_by_date.get(current_date, []):
                if any(position["stock_id"] == entry["stock_id"] for position in open_positions):
                    continue
                quantity = int(cash // entry["entry_price"])
                if config.lot_size > 1:
                    quantity = (quantity // config.lot_size) * config.lot_size
                while quantity > 0:
                    buy_cost = self.cost_model.estimate("BUY", entry["entry_price"], quantity)
                    required_cash = entry["entry_price"] * quantity + buy_cost.total
                    if required_cash <= cash:
                        break
                    quantity -= config.lot_size
                if quantity <= 0:
                    continue
                cash -= entry["entry_price"] * quantity + buy_cost.total
                open_positions.append(
                    {
                        **entry,
                        "quantity": quantity,
                        "buy_cost": buy_cost.total,
                        "buy_slippage": buy_cost.slippage,
                    }
                )

            equity = cash
            for position in open_positions:
                row = day_frame[day_frame["stock_id"].astype(str) == position["stock_id"]]
                if not row.empty:
                    equity += position["quantity"] * float(row.iloc[0]["close"])
                else:
                    equity += position["quantity"] * position["entry_price"]
            equity_rows.append({"date": current_date.date().isoformat(), "equity": equity})

        trades_frame = pd.DataFrame(trades)
        equity_curve = pd.DataFrame(equity_rows)
        metrics = performance_metrics(equity_curve, trades_frame, initial_cash=config.initial_cash)
        ending_equity = float(equity_curve["equity"].iloc[-1]) if not equity_curve.empty else config.initial_cash
        summary = {
            "start_date": config.start_date.isoformat(),
            "end_date": config.end_date.isoformat(),
            "initial_cash": config.initial_cash,
            "ending_equity": ending_equity,
            "net_profit": ending_equity - config.initial_cash,
            "return_pct": (ending_equity / config.initial_cash - 1) * 100,
            "trade_count": int(len(trades_frame)),
            "lot_size": config.lot_size,
        }
        return BenchmarkResult(trades=trades_frame, equity_curve=equity_curve, metrics=metrics, summary=summary)


def write_benchmark_report(result: BenchmarkResult, output_dir: str | Path, label: str = "benchmark") -> tuple[Path, Path, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    safe_label = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in label)
    trades_path = output / f"{safe_label}_trades.csv"
    equity_path = output / f"{safe_label}_equity_curve.csv"
    report_path = output / f"{safe_label}_report.md"
    result.trades.to_csv(trades_path, index=False)
    result.equity_curve.to_csv(equity_path, index=False)
    lines = [
        "# Benchmark Report",
        "",
        "Scope: fully execute T+1 Swing BUY signals from local historical daily data.",
        "Opening Range Breakout is skipped unless intraday bars are supplied.",
        "",
        "## Summary",
        "",
    ]
    for key, value in result.summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Metrics", ""])
    for key, value in result.metrics.items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "No broker login, app automation, or automatic order submission is performed.", ""])
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return trades_path, equity_path, report_path
