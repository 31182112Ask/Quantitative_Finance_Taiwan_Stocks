from __future__ import annotations

import pandas as pd


def bid_ask_imbalance(frame: pd.DataFrame) -> pd.Series:
    denom = (frame["bid_volume"] + frame["ask_volume"]).replace(0, pd.NA)
    return (frame["bid_volume"] - frame["ask_volume"]) / denom
