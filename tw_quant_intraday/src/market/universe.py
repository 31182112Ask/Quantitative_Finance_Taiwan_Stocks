from __future__ import annotations

import pandas as pd

from src.market.liquidity import filter_liquid


def build_universe(daily: pd.DataFrame, min_avg_turnover_20d: float) -> pd.DataFrame:
    required = {"date", "stock_id", "close", "volume"}
    missing = required - set(daily.columns)
    if missing:
        raise ValueError(f"daily data missing columns: {sorted(missing)}")
    liquid = filter_liquid(daily, min_avg_turnover_20d)
    return liquid[["stock_id"]].drop_duplicates().sort_values("stock_id").reset_index(drop=True)
