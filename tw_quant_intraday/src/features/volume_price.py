from __future__ import annotations

import pandas as pd


def relative_volume(frame: pd.DataFrame, window: int = 20) -> pd.Series:
    baseline = frame["volume"].rolling(window, min_periods=1).mean()
    return frame["volume"] / baseline.replace(0, pd.NA)


def turnover(frame: pd.DataFrame, price_col: str = "close", volume_col: str = "volume") -> pd.Series:
    return frame[price_col] * frame[volume_col]
