from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from src.calendar_tw import localize_taipei
from src.features.volatility import atr
from src.strategies.base import StrategySignal


def stock_selection_snapshot(daily: pd.DataFrame, stock_id: str, as_of: datetime) -> dict[str, Any]:
    """Score one stock for the first-pass universe filter."""
    current_time = localize_taipei(as_of)
    stock = daily[daily["stock_id"].astype(str) == str(stock_id)].copy()
    if stock.empty:
        return {
            "stock_id": str(stock_id),
            "stock_name": "",
            "selected": False,
            "score": 0,
            "reason": "no daily data",
            "close": None,
            "avg_turnover_20d": 0.0,
            "trend": "unknown",
        }

    stock["date"] = pd.to_datetime(stock["date"])
    stock = stock[stock["date"] <= pd.Timestamp(current_time.date())].sort_values("date")
    if len(stock) < 20:
        latest = stock.iloc[-1]
        return {
            "stock_id": str(stock_id),
            "stock_name": str(latest.get("stock_name", "")),
            "selected": False,
            "score": 10,
            "reason": "history shorter than 20 sessions",
            "close": float(latest["close"]),
            "avg_turnover_20d": float((stock["close"].astype(float) * stock["volume"].astype(float)).mean()),
            "trend": "insufficient",
        }

    stock["ma5"] = stock["close"].astype(float).rolling(5, min_periods=5).mean()
    stock["ma20"] = stock["close"].astype(float).rolling(20, min_periods=20).mean()
    stock["prior_high5"] = stock["high"].astype(float).shift(1).rolling(5, min_periods=5).max()
    stock["turnover_calc"] = stock["close"].astype(float) * stock["volume"].astype(float)
    stock["avg_turnover_20d"] = stock["turnover_calc"].rolling(20, min_periods=5).mean()
    latest = stock.iloc[-1]

    close = float(latest["close"])
    ma5 = float(latest["ma5"])
    ma20 = float(latest["ma20"])
    prior_high = float(latest["prior_high5"])
    avg_turnover = float(latest["avg_turnover_20d"])
    volume_20 = float(stock["volume"].astype(float).tail(20).mean())
    recent_volume = float(stock["volume"].astype(float).tail(5).mean())

    trend_ok = close > ma5 >= ma20
    range_ok = close >= prior_high * 0.995
    liquidity_ok = avg_turnover >= 50_000_000
    volume_ok = recent_volume >= volume_20 * 0.75
    score = 0
    score += 30 if trend_ok else 0
    score += 25 if range_ok else 0
    score += 25 if liquidity_ok else 0
    score += 20 if volume_ok else 0
    selected = score >= 70

    reasons = []
    reasons.append("trend above 5d/20d MA" if trend_ok else "trend not aligned")
    reasons.append("near 5d breakout" if range_ok else "not near range high")
    reasons.append("liquid" if liquidity_ok else "liquidity below filter")
    reasons.append("volume confirmed" if volume_ok else "volume below filter")

    return {
        "stock_id": str(stock_id),
        "stock_name": str(latest.get("stock_name", "")),
        "selected": selected,
        "score": score,
        "reason": "; ".join(reasons),
        "close": close,
        "ma5": ma5,
        "ma20": ma20,
        "avg_turnover_20d": avg_turnover,
        "trend": "bullish" if trend_ok else "neutral",
    }


def balanced_t_plus_one_signal(daily: pd.DataFrame, stock_id: str, as_of: datetime) -> StrategySignal:
    """A less strict, explicitly labelled recommendation signal for broad scans and benchmarks."""
    current_time = localize_taipei(as_of)
    stock = daily[daily["stock_id"].astype(str) == str(stock_id)].copy()
    if stock.empty:
        return StrategySignal.hold(str(stock_id), "T_PLUS_ONE_SWING", "no daily data", current_time)

    stock["date"] = pd.to_datetime(stock["date"])
    stock = stock[stock["date"] <= pd.Timestamp(current_time.date())].sort_values("date")
    if len(stock) < 25:
        return StrategySignal.hold(str(stock_id), "T_PLUS_ONE_SWING", "balanced profile needs 25 sessions", current_time)

    stock["ma5"] = stock["close"].astype(float).rolling(5, min_periods=5).mean()
    stock["ma20"] = stock["close"].astype(float).rolling(20, min_periods=20).mean()
    stock["prior_high5"] = stock["high"].astype(float).shift(1).rolling(5, min_periods=5).max()
    stock["vol20"] = stock["volume"].astype(float).rolling(20, min_periods=5).mean()
    stock["atr"] = atr(stock, 14)
    latest = stock.iloc[-1]
    required = ["ma5", "ma20", "prior_high5", "vol20", "atr"]
    if any(pd.isna(latest[col]) for col in required):
        return StrategySignal.hold(str(stock_id), "T_PLUS_ONE_SWING", "insufficient balanced indicators", current_time)

    close = float(latest["close"])
    ma5 = float(latest["ma5"])
    ma20 = float(latest["ma20"])
    prior_high = float(latest["prior_high5"])
    volume = float(latest["volume"])
    vol20 = float(latest["vol20"])
    if close <= ma5 or ma5 < ma20:
        return StrategySignal.hold(str(stock_id), "T_PLUS_ONE_SWING", "balanced trend filter not met", current_time)
    if close < prior_high * 0.995:
        return StrategySignal.hold(str(stock_id), "T_PLUS_ONE_SWING", "balanced range filter not met", current_time)
    if volume < vol20 * 0.75:
        return StrategySignal.hold(str(stock_id), "T_PLUS_ONE_SWING", "balanced volume filter not met", current_time)

    atr_value = float(latest["atr"])
    stop = round(max(close - atr_value * 1.8, close * 0.955), 2)
    take_profit = round(close + atr_value * 3.2, 2)
    breakout_margin = max((close - prior_high) / prior_high, 0.0) if prior_high > 0 else 0.0
    volume_ratio = volume / vol20 if vol20 > 0 else 1.0
    confidence = min(0.82, 0.52 + min(breakout_margin, 0.04) * 2.5 + min(max(volume_ratio - 0.75, 0), 1.0) * 0.12)

    return StrategySignal(
        stock_id=str(stock_id),
        stock_name=str(latest.get("stock_name", "")),
        side="BUY",
        signal_type="T_PLUS_ONE_SWING",
        confidence=round(confidence, 2),
        entry_price=close,
        stop_loss=stop,
        take_profit=take_profit,
        max_position_value=None,
        reason=(
            f"balanced candidate: close {close:.2f} near 5d high {prior_high:.2f}; "
            f"MA5 {ma5:.2f} >= MA20 {ma20:.2f}; volume {volume_ratio:.2f}x 20d"
        ),
        invalid_reason="",
        created_at=current_time,
    )
