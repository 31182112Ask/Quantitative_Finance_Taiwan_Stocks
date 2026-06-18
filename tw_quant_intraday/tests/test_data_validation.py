import pandas as pd

from src.data_sources.data_cache import DAILY_COLUMNS, INTRADAY_COLUMNS, validate_daily, validate_intraday
from src.data_sources.intraday_quote import LocalIntradayQuoteProvider


def test_daily_validation_rejects_missing_columns():
    result = validate_daily(pd.DataFrame({"date": ["2026-06-18"]}))
    assert not result.ok
    assert "missing columns" in result.errors[0]


def test_intraday_provider_does_not_fake_realtime_when_csv_missing(tmp_path):
    result = LocalIntradayQuoteProvider(tmp_path).load("2330", "2026-06-18")
    assert result.data.empty
    assert not result.is_realtime
    assert "missing local intraday CSV" in result.status


def test_intraday_validation_accepts_standard_schema():
    frame = pd.DataFrame(
        [{
            "datetime": "2026-06-18 09:01:00",
            "stock_id": "2330",
            "price": 100,
            "volume": 1000,
            "bid_price": 99.9,
            "ask_price": 100.1,
            "bid_volume": 500,
            "ask_volume": 600,
            "source": "mock_csv",
            "updated_at": "2026-06-18 09:01:10",
        }],
        columns=INTRADAY_COLUMNS,
    )
    assert validate_intraday(frame).ok
