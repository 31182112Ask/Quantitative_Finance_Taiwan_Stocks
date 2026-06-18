from __future__ import annotations

import pandas as pd


def summary_counts(signals: pd.DataFrame) -> dict[str, int]:
    if signals.empty:
        return {"signals": 0, "actionable": 0, "blocked": 0}
    actionable = signals[signals["side"].isin(["BUY", "SELL", "CLOSE"])]
    blocked = signals[signals.get("invalid_reason", "") != ""]
    return {"signals": int(len(signals)), "actionable": int(len(actionable)), "blocked": int(len(blocked))}
