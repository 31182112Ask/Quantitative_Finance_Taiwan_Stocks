from src.ui.services import (
    BenchmarkUiRequest,
    StrategyBatchScanRequest,
    StrategyScanRequest,
    run_benchmark_ui,
    run_strategy_batch_scan,
    run_strategy_scan,
)


def test_strategy_scan_service_returns_signal_and_risk_context():
    result = run_strategy_scan(
        StrategyScanRequest(
            strategy="opening_range_breakout",
            stock_id="2330",
            trade_date="2026-06-18",
            trade_time="10:00:00",
            equity=1_000_000,
            avg_turnover_20d=100_000_000,
            intraday_source="mock",
            write_ticket=False,
        )
    )
    assert result["signal"]["signal_type"] == "OPENING_RANGE_BREAKOUT"
    assert result["mode"] == "manual_ticket_only"
    assert "automatic order" in result["safety"]


def test_benchmark_ui_service_returns_summary_and_files():
    result = run_benchmark_ui(
        BenchmarkUiRequest(
            data_file="data/daily/twse_2026_05_benchmark.csv",
            start="2026-05-01",
            end="2026-05-31",
            initial_cash=10_000,
            lot_size=1,
            label="test_ui_benchmark",
            write_files=False,
        )
    )
    assert result["summary"]["initial_cash"] == 10_000
    assert "return_pct" in result["summary"]
    assert "trades" in result
    assert result["summary"]["trade_count"] > 0


def test_strategy_batch_scan_covers_selection_intraday_and_short_term():
    result = run_strategy_batch_scan(
        StrategyBatchScanRequest(
            daily_file="data/daily/twse_2026_05_benchmark.csv",
            trade_date="2026-05-29",
            trade_time="10:00:00",
            equity=1_000_000,
            intraday_source="local",
            write_ticket=False,
        )
    )
    assert result["summary"]["stock_count"] >= 2
    assert result["summary"]["selected_count"] >= 1
    assert "stock_selection" in result
    assert "intraday" in result
    assert "short_term" in result
    assert result["summary"]["short_term_signal_count"] >= 1
    assert result["mode"] == "manual_ticket_only"
