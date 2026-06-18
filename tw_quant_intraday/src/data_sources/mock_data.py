from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd


def make_mock_daily(stock_id: str = "2330", stock_name: str = "TSMC", rows: int = 90) -> pd.DataFrame:
    start = pd.Timestamp("2026-01-02")
    records = []
    trading_day = 0
    offset = 0
    while trading_day < rows:
        day = start + pd.Timedelta(days=offset)
        offset += 1
        if day.weekday() >= 5:
            continue
        close = 50 + trading_day * 0.08
        volume = 2_000_000 + trading_day * 10_000
        records.append({
            "date": day.date().isoformat(),
            "stock_id": stock_id,
            "stock_name": stock_name,
            "open": round(close - 0.4, 2),
            "high": round(close + 0.8, 2),
            "low": round(close - 1.0, 2),
            "close": round(close, 2),
            "volume": volume,
            "turnover": round(close * volume, 2),
            "source": "mock_demo_daily",
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        })
        trading_day += 1
    breakout_index = max(rows - 10, 65)
    prior_high = max(record["high"] for record in records[breakout_index - 20 : breakout_index])
    records[breakout_index]["close"] = round(prior_high + 2.0, 2)
    records[breakout_index]["high"] = round(records[breakout_index]["close"] + 0.8, 2)
    records[breakout_index]["volume"] = 5_000_000
    records[breakout_index]["turnover"] = round(records[breakout_index]["close"] * records[breakout_index]["volume"], 2)
    return pd.DataFrame(records)


def make_mock_intraday(stock_id: str = "2330", trade_date: str = "2026-06-18") -> pd.DataFrame:
    start = datetime.fromisoformat(f"{trade_date} 09:00:00")
    records = []
    for minute in range(40):
        price = 100 + min(minute, 14) * 0.05
        volume = 1000
        if minute >= 20:
            price = 102.5 + (minute - 20) * 0.03
            volume = 3000
        records.append({
            "datetime": start + timedelta(minutes=minute),
            "stock_id": stock_id,
            "price": round(price, 2),
            "volume": volume,
            "bid_price": round(price - 0.05, 2),
            "ask_price": round(price + 0.05, 2),
            "bid_volume": 500,
            "ask_volume": 600,
            "source": "mock_demo_intraday_not_realtime",
            "updated_at": (start + timedelta(minutes=minute, seconds=5)).isoformat(sep=" "),
        })
    return pd.DataFrame(records)
