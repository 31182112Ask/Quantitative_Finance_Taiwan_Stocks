from __future__ import annotations

from pathlib import Path

import pandas as pd


def write_market_summary(output_dir: str | Path, universe_count: int, notes: list[str] | None = None) -> Path:
    path = Path(output_dir) / "market_summary.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    notes = notes or []
    content = [
        "# Daily Market Summary",
        "",
        f"Tradable universe count: {universe_count}",
        "",
        "## Notes",
        *(f"- {note}" for note in notes),
        "",
    ]
    path.write_text("\n".join(content), encoding="utf-8")
    return path


def write_signal_report(output_dir: str | Path, signals: pd.DataFrame, blocked_count: int = 0) -> Path:
    path = Path(output_dir) / "signal_report.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Intraday Signal Report",
        "",
        f"Signals: {len(signals)}",
        f"Blocked by risk: {blocked_count}",
        "",
    ]
    if signals.empty:
        lines.append("No trade recommendation is generated without risk review.")
    else:
        lines.append("```text")
        lines.append(signals.to_string(index=False))
        lines.append("```")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_performance_report(output_dir: str | Path, metrics: dict[str, float]) -> Path:
    path = Path(output_dir) / "performance.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Paper Trading Performance", ""]
    for key, value in metrics.items():
        lines.append(f"- {key}: {value}")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
