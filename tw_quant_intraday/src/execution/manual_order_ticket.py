from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.execution.broker_checklist import checklist_markdown
from src.strategies.base import StrategySignal

TICKET_COLUMNS = [
    "date",
    "time",
    "mode",
    "stock_id",
    "stock_name",
    "side",
    "suggested_price",
    "max_price",
    "stop_loss",
    "take_profit",
    "suggested_quantity",
    "suggested_amount",
    "strategy",
    "reason",
    "risk_notes",
    "manual_confirm_required",
]


def signal_to_ticket_row(signal: StrategySignal, quantity: int, risk_notes: str, mode: str = "live_assist") -> dict:
    if signal.side not in {"BUY", "SELL", "CLOSE"}:
        raise ValueError("only actionable signals can become manual tickets")
    if signal.entry_price is None:
        raise ValueError("actionable signal must include entry_price")
    amount = signal.entry_price * quantity
    return {
        "date": signal.created_at.date().isoformat(),
        "time": signal.created_at.time().isoformat(timespec="minutes"),
        "mode": mode,
        "stock_id": signal.stock_id,
        "stock_name": signal.stock_name,
        "side": signal.side,
        "suggested_price": signal.entry_price,
        "max_price": signal.entry_price,
        "stop_loss": signal.stop_loss,
        "take_profit": signal.take_profit,
        "suggested_quantity": quantity,
        "suggested_amount": amount,
        "strategy": signal.signal_type,
        "reason": signal.reason,
        "risk_notes": risk_notes,
        "manual_confirm_required": True,
    }


def write_manual_order_ticket(rows: list[dict], output_dir: str | Path) -> tuple[Path, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    csv_path = output / "manual_order_ticket.csv"
    md_path = output / "manual_order_ticket.md"
    frame = pd.DataFrame(rows, columns=TICKET_COLUMNS)
    frame.to_csv(csv_path, index=False)
    lines = [
        "# Manual Order Ticket",
        "",
        "This file is a manual checklist only. It does not place orders, log in to any broker, or submit instructions.",
        "",
    ]
    if frame.empty:
        lines.append("No approved actionable signals.")
    else:
        lines.append("```text")
        lines.append(frame.to_string(index=False))
        lines.append("```")
    lines.extend(["", "## Manual Broker Checklist", "", checklist_markdown(), ""])
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return csv_path, md_path
