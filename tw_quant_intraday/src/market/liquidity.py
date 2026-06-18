from __future__ import annotations

import pandas as pd


def add_turnover_columns(daily: pd.DataFrame) -> pd.DataFrame:
    result = daily.copy()
    result["turnover_calc"] = result["close"] * result["volume"]
    result["avg_turnover_20d"] = (
        result.sort_values(["stock_id", "date"])
        .groupby("stock_id")["turnover_calc"]
        .transform(lambda s: s.rolling(20, min_periods=1).mean())
    )
    return result


def filter_liquid(daily: pd.DataFrame, min_avg_turnover_20d: float) -> pd.DataFrame:
    enriched = add_turnover_columns(daily)
    return enriched[enriched["avg_turnover_20d"] >= min_avg_turnover_20d].copy()
