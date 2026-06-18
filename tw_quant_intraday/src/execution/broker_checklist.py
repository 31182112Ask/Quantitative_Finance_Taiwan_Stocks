from __future__ import annotations


MANUAL_BROKER_CHECKLIST = [
    "Confirm the stock is tradable.",
    "Confirm liquidity and current quoted spread.",
    "Confirm current price distance from suggested price.",
    "Confirm single-trade risk.",
    "Confirm today's cumulative trade count.",
    "Confirm today's cumulative PnL.",
    "Confirm the market is not near close.",
    "Open the broker app manually.",
    "Enter the order manually.",
    "Review and submit manually only if you accept the risk.",
]


def checklist_markdown() -> str:
    return "\n".join(f"- [ ] {item}" for item in MANUAL_BROKER_CHECKLIST)
