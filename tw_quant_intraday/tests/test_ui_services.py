from src.ui.services import BenchmarkUiRequest, StrategyScanRequest, run_benchmark_ui, run_strategy_scan


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
