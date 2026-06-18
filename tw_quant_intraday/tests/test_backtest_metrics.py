import pandas as pd

from src.backtest.metrics import max_drawdown, performance_metrics


def test_backtest_metrics_include_required_fields():
    equity = pd.DataFrame({"date": ["d1", "d2", "d3"], "equity": [100, 110, 105]})
    trades = pd.DataFrame({
        "pnl": [10, -3],
        "notional": [100, 100],
        "cost": [1, 1],
        "slippage": [0.2, 0.2],
        "holding_minutes": [270, 540],
    })
    metrics = performance_metrics(equity, trades, initial_cash=100)
    for key in [
        "total_return",
        "cagr",
        "max_drawdown",
        "sharpe",
        "sortino",
        "win_rate",
        "profit_factor",
        "avg_win",
        "avg_loss",
        "max_consecutive_losses",
        "turnover",
        "trade_count",
        "avg_holding_minutes",
        "cost_total",
        "slippage_total",
    ]:
        assert key in metrics
    assert metrics["trade_count"] == 2
    assert metrics["cost_total"] == 2


def test_max_drawdown_is_negative_for_decline():
    assert max_drawdown(pd.Series([100, 120, 90])) == -0.25
