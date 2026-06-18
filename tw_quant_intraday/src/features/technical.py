from __future__ import annotations

import pandas as pd


def moving_average(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window, min_periods=window).mean()


def returns(series: pd.Series, periods: int = 1) -> pd.Series:
    return series.pct_change(periods)


def vwap(frame: pd.DataFrame, price_col: str = "price", volume_col: str = "volume") -> pd.Series:
    value = (frame[price_col] * frame[volume_col]).cumsum()
    volume = frame[volume_col].cumsum().replace(0, pd.NA)
    return value / volume
