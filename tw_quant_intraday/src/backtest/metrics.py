from __future__ import annotations

import numpy as np
import pandas as pd


def max_consecutive_losses(pnls: pd.Series) -> int:
    longest = current = 0
    for value in pnls:
        if value < 0:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def max_drawdown(equity: pd.Series) -> float:
    if equity.empty:
        return 0.0
    peak = equity.cummax()
    drawdown = equity / peak - 1
    return float(drawdown.min())


def performance_metrics(
    equity_curve: pd.DataFrame,
    trades: pd.DataFrame,
    *,
    initial_cash: float,
    periods_per_year: int = 252,
) -> dict[str, float]:
    if equity_curve.empty:
        ending_equity = initial_cash
        returns = pd.Series(dtype=float)
        equity = pd.Series([initial_cash])
    else:
        equity = equity_curve["equity"].astype(float)
        ending_equity = float(equity.iloc[-1])
        returns = equity.pct_change().dropna()
    total_return = ending_equity / initial_cash - 1
    years = max(len(equity) / periods_per_year, 1 / periods_per_year)
    cagr = (ending_equity / initial_cash) ** (1 / years) - 1 if ending_equity > 0 else -1.0
    downside = returns[returns < 0]
    sharpe = float(np.sqrt(periods_per_year) * returns.mean() / returns.std(ddof=0)) if returns.std(ddof=0) > 0 else 0.0
    sortino = float(np.sqrt(periods_per_year) * returns.mean() / downside.std(ddof=0)) if downside.std(ddof=0) > 0 else 0.0

    if trades.empty:
        pnls = pd.Series(dtype=float)
        wins = pd.Series(dtype=float)
        losses = pd.Series(dtype=float)
        trade_count = 0
        turnover = 0.0
        cost_total = 0.0
        slippage_total = 0.0
        avg_holding_minutes = 0.0
    else:
        pnls = trades["pnl"].astype(float)
        wins = pnls[pnls > 0]
        losses = pnls[pnls < 0]
        trade_count = int(len(trades))
        turnover = float(trades.get("notional", pd.Series(dtype=float)).sum())
        cost_total = float(trades.get("cost", pd.Series(dtype=float)).sum())
        slippage_total = float(trades.get("slippage", pd.Series(dtype=float)).sum())
        avg_holding_minutes = float(trades.get("holding_minutes", pd.Series([0] * trade_count)).mean())

    gross_profit = float(wins.sum()) if not wins.empty else 0.0
    gross_loss = abs(float(losses.sum())) if not losses.empty else 0.0
    return {
        "total_return": float(total_return),
        "cagr": float(cagr),
        "max_drawdown": max_drawdown(equity),
        "sharpe": sharpe,
        "sortino": sortino,
        "win_rate": float((pnls > 0).mean()) if len(pnls) else 0.0,
        "profit_factor": gross_profit / gross_loss if gross_loss > 0 else (float("inf") if gross_profit > 0 else 0.0),
        "avg_win": float(wins.mean()) if not wins.empty else 0.0,
        "avg_loss": float(losses.mean()) if not losses.empty else 0.0,
        "max_consecutive_losses": float(max_consecutive_losses(pnls)),
        "turnover": turnover,
        "trade_count": float(trade_count),
        "avg_holding_minutes": avg_holding_minutes,
        "cost_total": cost_total,
        "slippage_total": slippage_total,
    }
