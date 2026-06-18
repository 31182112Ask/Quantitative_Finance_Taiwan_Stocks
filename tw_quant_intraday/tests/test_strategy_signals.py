from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

from src.strategies.opening_range_breakout import OpeningRangeBreakoutStrategy
from src.strategies.t_plus_one_swing import TPlusOneSwingStrategy

TAIPEI = ZoneInfo("Asia/Taipei")


def test_opening_range_breakout_emits_buy_after_valid_breakout():
    base = datetime(2026, 6, 18, 9, 0)
    rows = []
    for i in range(20):
        rows.append({
            "datetime": base + timedelta(minutes=i),
            "stock_id": "2330",
            "price": 100 + min(i, 10) * 0.1,
            "volume": 1000,
            "bid_price": 100,
            "ask_price": 100.2,
            "bid_volume": 100,
            "ask_volume": 100,
            "source": "mock_csv",
            "updated_at": base + timedelta(minutes=i),
        })
    rows[-1]["price"] = 103
    rows[-1]["volume"] = 3000
    signal = OpeningRangeBreakoutStrategy().generate(
        pd.DataFrame(rows),
        "2330",
        datetime(2026, 6, 18, 9, 20, tzinfo=TAIPEI),
    )
    assert signal.side == "BUY"
    assert signal.signal_type == "OPENING_RANGE_BREAKOUT"
    assert signal.entry_price == 103


def test_opening_range_breakout_holds_without_intraday_data():
    signal = OpeningRangeBreakoutStrategy().generate(
        pd.DataFrame(),
        "2330",
        datetime(2026, 6, 18, 9, 20, tzinfo=TAIPEI),
    )
    assert signal.side == "HOLD"
    assert "no intraday data" in signal.invalid_reason


def test_t_plus_one_swing_emits_buy_for_breakout_daily_setup():
    rows = []
    for i in range(70):
        close = 100 + i * 0.2
        rows.append({
            "date": pd.Timestamp("2026-01-01") + pd.Timedelta(days=i),
            "stock_id": "2330",
            "stock_name": "TSMC",
            "open": close - 0.5,
            "high": close + 0.5,
            "low": close - 1,
            "close": close,
            "volume": 1000 + i * 5,
            "turnover": close * (1000 + i * 5),
            "source": "mock_csv",
            "updated_at": "2026-06-18",
        })
    rows[-1]["close"] = rows[-2]["high"] + 2
    rows[-1]["high"] = rows[-1]["close"] + 0.5
    rows[-1]["volume"] = 5000
    signal = TPlusOneSwingStrategy().generate(
        pd.DataFrame(rows),
        "2330",
        datetime(2026, 6, 18, 14, 0, tzinfo=TAIPEI),
    )
    assert signal.side == "BUY"
    assert signal.signal_type == "T_PLUS_ONE_SWING"


def test_t_plus_one_swing_holds_without_enough_history():
    signal = TPlusOneSwingStrategy().generate(
        pd.DataFrame([{"stock_id": "2330", "close": 100, "high": 101, "volume": 1000}]),
        "2330",
        datetime(2026, 6, 18, 14, 0, tzinfo=TAIPEI),
    )
    assert signal.side == "HOLD"
    assert "insufficient" in signal.invalid_reason
