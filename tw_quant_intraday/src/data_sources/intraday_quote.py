from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.data_sources.data_cache import INTRADAY_COLUMNS, validate_intraday


@dataclass(frozen=True)
class IntradayLoadResult:
    data: pd.DataFrame
    source: str
    is_realtime: bool
    status: str


class LocalIntradayQuoteProvider:
    """Loads local intraday CSV snapshots without pretending they are realtime."""

    def __init__(self, data_dir: str | Path) -> None:
        self.data_dir = Path(data_dir)

    def load(self, stock_id: str, trade_date: str) -> IntradayLoadResult:
        path = self.data_dir / f"{trade_date}_{stock_id}.csv"
        if not path.exists():
            return IntradayLoadResult(
                data=pd.DataFrame(columns=INTRADAY_COLUMNS),
                source="local_csv",
                is_realtime=False,
                status=f"missing local intraday CSV: {path}",
            )
        frame = pd.read_csv(path)
        result = validate_intraday(frame)
        if not result.ok:
            return IntradayLoadResult(frame, "local_csv", False, "; ".join(result.errors))
        frame["datetime"] = pd.to_datetime(frame["datetime"])
        return IntradayLoadResult(frame.sort_values("datetime"), "local_csv", False, "ok")
