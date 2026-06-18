from __future__ import annotations

from pathlib import Path

from src.execution.manual_order_ticket import signal_to_ticket_row, write_manual_order_ticket
from src.risk.risk_manager import RiskDecision
from src.strategies.base import StrategySignal


def export_approved_manual_tickets(
    signals: list[StrategySignal],
    risk_decisions: list[RiskDecision],
    output_dir: str | Path,
) -> tuple[Path, Path]:
    rows = []
    for signal, decision in zip(signals, risk_decisions):
        if signal.side == "HOLD" or not decision.approved:
            continue
        rows.append(signal_to_ticket_row(signal, decision.size.quantity, "; ".join(decision.notes)))
    return write_manual_order_ticket(rows, output_dir)
