from datetime import datetime
from zoneinfo import ZoneInfo

from src.risk.risk_manager import RiskLimits, RiskManager, RiskState


TAIPEI = ZoneInfo("Asia/Taipei")


def test_risk_manager_approves_valid_entry_with_manual_note():
    manager = RiskManager(RiskLimits(min_avg_turnover_20d=1))
    decision = manager.evaluate_entry(
        stock_id="2330",
        side="BUY",
        entry_price=100,
        stop_loss=96,
        current_time=datetime(2026, 6, 18, 10, 0, tzinfo=TAIPEI),
        state=RiskState(equity=1_000_000),
        avg_turnover_20d=10_000_000,
        data_is_fresh=True,
    )
    assert decision.approved
    assert decision.size.quantity > 0
    assert "manual confirmation required" in " ".join(decision.notes)


def test_risk_manager_blocks_stale_data():
    manager = RiskManager(RiskLimits(min_avg_turnover_20d=1))
    decision = manager.evaluate_entry(
        stock_id="2330",
        side="BUY",
        entry_price=100,
        stop_loss=96,
        current_time=datetime(2026, 6, 18, 10, 0, tzinfo=TAIPEI),
        state=RiskState(equity=1_000_000),
        avg_turnover_20d=10_000_000,
        data_is_fresh=False,
    )
    assert not decision.approved
    assert "stale" in decision.reason


def test_risk_manager_blocks_over_daily_loss_limit():
    manager = RiskManager(RiskLimits(max_daily_loss_pct=0.02, min_avg_turnover_20d=1))
    decision = manager.evaluate_entry(
        stock_id="2330",
        side="BUY",
        entry_price=100,
        stop_loss=96,
        current_time=datetime(2026, 6, 18, 10, 0, tzinfo=TAIPEI),
        state=RiskState(equity=1_000_000, daily_pnl=-20_000),
        avg_turnover_20d=10_000_000,
        data_is_fresh=True,
    )
    assert not decision.approved
    assert "daily loss" in decision.reason
