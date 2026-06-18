from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

DAILY_COLUMNS = [
    "date",
    "stock_id",
    "stock_name",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "turnover",
    "source",
    "updated_at",
]

INTRADAY_COLUMNS = [
    "datetime",
    "stock_id",
    "price",
    "volume",
    "bid_price",
    "ask_price",
    "bid_volume",
    "ask_volume",
    "source",
    "updated_at",
]


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    errors: list[str]


def validate_columns(frame: pd.DataFrame, required: list[str]) -> ValidationResult:
    missing = [col for col in required if col not in frame.columns]
    return ValidationResult(ok=not missing, errors=[f"missing columns: {missing}"] if missing else [])


def validate_daily(frame: pd.DataFrame) -> ValidationResult:
    errors: list[str] = []
    column_check = validate_columns(frame, DAILY_COLUMNS)
    errors.extend(column_check.errors)
    if errors:
        return ValidationResult(False, errors)
    numeric = ["open", "high", "low", "close", "volume", "turnover"]
    if frame[numeric].isna().any().any():
        errors.append("daily data contains missing numeric values")
    if (frame[["open", "high", "low", "close"]] <= 0).any().any():
        errors.append("daily prices must be positive")
    if (frame["high"] < frame["low"]).any():
        errors.append("daily high cannot be below low")
    if ((frame["close"] > frame["high"]) | (frame["close"] < frame["low"])).any():
        errors.append("daily close must be inside high-low range")
    return ValidationResult(not errors, errors)


def validate_intraday(frame: pd.DataFrame) -> ValidationResult:
    errors: list[str] = []
    column_check = validate_columns(frame, INTRADAY_COLUMNS)
    errors.extend(column_check.errors)
    if errors:
        return ValidationResult(False, errors)
    numeric = ["price", "volume", "bid_price", "ask_price", "bid_volume", "ask_volume"]
    if frame[numeric].isna().any().any():
        errors.append("intraday data contains missing numeric values")
    if (frame[["price", "bid_price", "ask_price"]] <= 0).any().any():
        errors.append("intraday prices must be positive")
    if (frame["ask_price"] < frame["bid_price"]).any():
        errors.append("ask price cannot be below bid price")
    return ValidationResult(not errors, errors)


class CsvDataCache:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def read(self, relative_path: str | Path) -> pd.DataFrame:
        path = self.root / relative_path
        if not path.exists():
            return pd.DataFrame()
        return pd.read_csv(path)

    def write(self, frame: pd.DataFrame, relative_path: str | Path) -> Path:
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(path, index=False)
        return path
