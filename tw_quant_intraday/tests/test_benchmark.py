from datetime import date

import pandas as pd
import pytest

from src.backtest.benchmark import BenchmarkConfig, RecommendedStrategyBenchmark, write_benchmark_report


def _daily_frame(source: str = "twse_official_public") -> pd.DataFrame:
    rows = []
    for i in range(90):
        day = pd.Timestamp("2026-01-02") + pd.Timedelta(days=i)
        close = 50 + i * 0.1
        rows.append(
            {
                "date": day.date().isoformat(),
                "stock_id": "1234",
                "stock_name": "TEST",
                "open": close - 0.2,
                "high": close + 0.5,
                "low": close - 0.5,
                "close": close,
                "volume": 1_000_000 + i,
                "turnover": close * (1_000_000 + i),
                "source": source,
                "updated_at": "2026-06-18T00:00:00+08:00",
            }
        )
    rows[75]["close"] = rows[74]["high"] + 2
    rows[75]["high"] = rows[75]["close"] + 1
    rows[75]["volume"] = 3_000_000
    rows[75]["turnover"] = rows[75]["close"] * rows[75]["volume"]
    return pd.DataFrame(rows)


def test_benchmark_refuses_mock_data_by_default():
    benchmark = RecommendedStrategyBenchmark()
    with pytest.raises(ValueError, match="refuses mock"):
        benchmark.run(
            _daily_frame("mock_demo_daily"),
            BenchmarkConfig(date(2026, 3, 1), date(2026, 3, 31)),
        )


def test_benchmark_runs_and_writes_outputs(tmp_path):
    benchmark = RecommendedStrategyBenchmark()
    result = benchmark.run(
        _daily_frame(),
        BenchmarkConfig(date(2026, 3, 1), date(2026, 3, 31), initial_cash=10_000, lot_size=1),
    )
    assert "ending_equity" in result.summary
    assert result.summary["initial_cash"] == 10_000
    assert result.summary["trade_count"] > 0
    paths = write_benchmark_report(result, tmp_path)
    for path in paths:
        assert path.exists()
