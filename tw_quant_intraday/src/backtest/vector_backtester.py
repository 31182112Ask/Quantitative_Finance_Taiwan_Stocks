from __future__ import annotations

import pandas as pd


def buy_and_hold_baseline(daily: pd.DataFrame, initial_cash: float = 1_000_000) -> pd.DataFrame:
    if daily.empty:
        return pd.DataFrame(columns=["date", "equity"])
    stock = daily.sort_values("date")
    first = float(stock.iloc[0]["close"])
    shares = initial_cash / first
    result = stock[["date"]].copy()
    result["equity"] = shares * stock["close"].astype(float)
    return result
