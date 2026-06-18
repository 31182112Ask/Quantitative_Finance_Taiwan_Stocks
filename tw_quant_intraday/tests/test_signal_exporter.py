from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from src.execution.manual_order_ticket import TICKET_COLUMNS, write_manual_order_ticket
from src.execution.signal_exporter import export_approved_manual_tickets
from src.risk.position_sizing import PositionSizeResult
from src.risk.risk_manager import RiskDecision
from src.strategies.base import StrategySignal


def test_manual_order_ticket_has_required_columns(tmp_path):
    signal = StrategySignal(
        stock_id="2330",
        stock_name="TSMC",
        side="BUY",
        signal_type="T_PLUS_ONE_SWING",
        confidence=0.6,
        entry_price=100,
        stop_loss=96,
        take_profit=107,
        max_position_value=100000,
        reason="test",
        invalid_reason="",
        created_at=datetime(2026, 6, 18, 10, 0, tzinfo=ZoneInfo("Asia/Taipei")),
    )
    from src.execution.manual_order_ticket import signal_to_ticket_row

    row = signal_to_ticket_row(signal, 1000, "manual confirmation required")
    csv_path, md_path = write_manual_order_ticket([row], tmp_path)
    frame = pd.read_csv(csv_path)
    assert list(frame.columns) == TICKET_COLUMNS
    assert frame.iloc[0]["manual_confirm_required"] == True
    assert "does not place orders" in md_path.read_text(encoding="utf-8")


def test_empty_manual_order_ticket_is_allowed(tmp_path):
    csv_path, md_path = write_manual_order_ticket([], tmp_path)
    frame = pd.read_csv(csv_path)
    assert list(frame.columns) == TICKET_COLUMNS
    assert frame.empty
    assert "No approved actionable signals" in md_path.read_text(encoding="utf-8")


def test_blocked_risk_decision_is_not_exported(tmp_path):
    signal = StrategySignal(
        stock_id="2330",
        stock_name="TSMC",
        side="BUY",
        signal_type="OPENING_RANGE_BREAKOUT",
        confidence=0.7,
        entry_price=100,
        stop_loss=96,
        take_profit=108,
        max_position_value=100000,
        reason="test",
        invalid_reason="",
        created_at=datetime(2026, 6, 18, 10, 0, tzinfo=ZoneInfo("Asia/Taipei")),
    )
    decision = RiskDecision(
        approved=False,
        reason="daily turnover limit would be exceeded",
        size=PositionSizeResult(quantity=1000, amount=100000, risk_amount=4000),
        notes=["blocked by risk"],
    )
    csv_path, _ = export_approved_manual_tickets([signal], [decision], tmp_path)
    assert pd.read_csv(csv_path).empty
