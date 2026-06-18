from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.data_sources.data_cache import DAILY_COLUMNS, validate_daily


class LocalDailyCsvSource:
    def __init__(self, data_dir: str | Path) -> None:
        self.data_dir = Path(data_dir)

    def load(self, file_name: str = "daily.csv") -> pd.DataFrame:
        path = self.data_dir / file_name
        if not path.exists():
            return pd.DataFrame(columns=DAILY_COLUMNS)
        frame = pd.read_csv(path)
        result = validate_daily(frame)
        if not result.ok:
            raise ValueError("; ".join(result.errors))
        frame["date"] = pd.to_datetime(frame["date"]).dt.date
        return frame.sort_values(["stock_id", "date"]).reset_index(drop=True)
