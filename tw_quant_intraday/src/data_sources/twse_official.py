from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd
import requests

from src.data_sources.data_cache import DAILY_COLUMNS, validate_daily


def roc_date_to_iso(value: str) -> str:
    year, month, day = value.split("/")
    return f"{int(year) + 1911:04d}-{int(month):02d}-{int(day):02d}"


def parse_number(value: str) -> float:
    return float(value.replace(",", "").strip())


def month_starts(start: date, end: date) -> list[date]:
    months: list[date] = []
    current = date(start.year, start.month, 1)
    last = date(end.year, end.month, 1)
    while current <= last:
        months.append(current)
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)
    return months


@dataclass(frozen=True)
class TwseOfficialDailyClient:
    base_url: str = "https://www.twse.com.tw/exchangeReport/STOCK_DAY"

    def fetch_stock_month(self, stock_id: str, month: date) -> pd.DataFrame:
        params = {
            "response": "json",
            "date": f"{month.year:04d}{month.month:02d}01",
            "stockNo": stock_id,
        }
        response = requests.get(self.base_url, params=params, timeout=20)
        response.raise_for_status()
        payload = response.json()
        if payload.get("stat") != "OK":
            return pd.DataFrame(columns=DAILY_COLUMNS)
        title = str(payload.get("title", ""))
        stock_name = title.split(stock_id, 1)[-1].replace("各日成交資訊", "").strip() if stock_id in title else ""
        rows = []
        for row in payload.get("data", []):
            rows.append(
                {
                    "date": roc_date_to_iso(row[0]),
                    "stock_id": str(stock_id),
                    "stock_name": stock_name,
                    "open": parse_number(row[3]),
                    "high": parse_number(row[4]),
                    "low": parse_number(row[5]),
                    "close": parse_number(row[6]),
                    "volume": parse_number(row[1]),
                    "turnover": parse_number(row[2]),
                    "source": "twse_official_public",
                    "updated_at": pd.Timestamp.now(tz="Asia/Taipei").isoformat(),
                }
            )
        return pd.DataFrame(rows, columns=DAILY_COLUMNS)

    def fetch_range(self, stock_ids: list[str], start: date, end: date) -> pd.DataFrame:
        frames = []
        for stock_id in stock_ids:
            for month in month_starts(start, end):
                frames.append(self.fetch_stock_month(stock_id, month))
        if not frames:
            return pd.DataFrame(columns=DAILY_COLUMNS)
        frame = pd.concat(frames, ignore_index=True)
        if frame.empty:
            return frame
        frame["date"] = pd.to_datetime(frame["date"])
        frame = frame[(frame["date"].dt.date >= start) & (frame["date"].dt.date <= end)].copy()
        frame["date"] = frame["date"].dt.date.astype(str)
        result = validate_daily(frame)
        if not result.ok:
            raise ValueError("; ".join(result.errors))
        return frame.sort_values(["stock_id", "date"]).reset_index(drop=True)


def write_twse_daily_csv(frame: pd.DataFrame, path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output, index=False)
    return output
