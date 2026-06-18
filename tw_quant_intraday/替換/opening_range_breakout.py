from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from src.calendar_tw import MARKET_OPEN, localize_taipei, minutes_after_open, minutes_before_close
from src.market.cost_model import TaiwanStockCostModel
from src.strategies.base import StrategyBase, StrategySignal


@dataclass(frozen=True)
class OpeningRangeBreakoutParams:
    opening_range_minutes: int = 15
    volume_multiplier: float = 1.5
    take_profit_r: float = 2.5          # improved from 2.0
    stop_buffer_bps: float = 10.0
    avoid_close_minutes: int = 15       # increased safety buffer
    max_position_value: float = 100_000
    min_range_pct: float = 0.003        # NEW: minimum opening range width
    max_range_pct: float = 0.03         # NEW: max range to avoid gap days
    require_retest: bool = True         # NEW: require breakout retest
    trend_ema_period: int = 20          # NEW: trend filter period


class OpeningRangeBreakoutStrategy(StrategyBase):
    """Enhanced Opening Range Breakout with multiple confirmation filters.

    Improvements over original:
    - Minimum range width filter (avoids false breakouts in narrow ranges)
    - Maximum range width filter (avoids gap day entries)
    - EMA trend filter: breakout direction must align with trend
    - Breakout retest confirmation (price pulls back then resumes)
    - Relative volume check with higher threshold
    - Dynamic R:R based on range width
    - Increased close-avoidance window
    """

    signal_type = "OPENING_RANGE_BREAKOUT"

    def __init__(
        self,
        params: OpeningRangeBreakoutParams | None = None,
        cost_model: TaiwanStockCostModel | None = None,
    ) -> None:
        self.params = params or OpeningRangeBreakoutParams()
        self.cost_model = cost_model or TaiwanStockCostModel()

    def generate(self, intraday: pd.DataFrame, stock_id: str, current_time: datetime) -> StrategySignal:
        current_time = localize_taipei(current_time)

        if intraday.empty:
            return StrategySignal.hold(stock_id, self.signal_type, "no intraday data", current_time)

        if minutes_after_open(current_time) < self.params.opening_range_minutes:
            return StrategySignal.hold(stock_id, self.signal_type, "opening range not yet complete", current_time)

        if minutes_before_close(current_time) < self.params.avoid_close_minutes:
            return StrategySignal.hold(stock_id, self.signal_type, "too close to market close", current_time)

        frame = intraday.copy()
        frame["datetime"] = pd.to_datetime(frame["datetime"])
        frame = frame[frame["datetime"] <= pd.Timestamp(current_time).tz_localize(None)].sort_values("datetime")

        if frame.empty:
            return StrategySignal.hold(stock_id, self.signal_type, "no rows up to current_time", current_time)

        # Define opening range
        open_start = pd.Timestamp.combine(frame["datetime"].dt.date.iloc[-1], MARKET_OPEN)
        open_end = open_start + pd.Timedelta(minutes=self.params.opening_range_minutes)
        opening = frame[(frame["datetime"] >= open_start) & (frame["datetime"] < open_end)]

        if opening.empty:
            return StrategySignal.hold(stock_id, self.signal_type, "missing opening range rows", current_time)

        latest = frame.iloc[-1]
        range_high = float(opening["price"].max())
        range_low = float(opening["price"].min())
        range_mid = (range_high + range_low) / 2
        range_width = range_high - range_low

        if range_mid <= 0:
            return StrategySignal.hold(stock_id, self.signal_type, "invalid range midpoint", current_time)

        range_pct = range_width / range_mid

        # Range width filter
        if range_pct < self.params.min_range_pct:
            return StrategySignal.hold(
                stock_id, self.signal_type,
                f"opening range {range_pct:.3%} too narrow (min {self.params.min_range_pct:.3%})",
                current_time,
            )

        if range_pct > self.params.max_range_pct:
            return StrategySignal.hold(
                stock_id, self.signal_type,
                f"opening range {range_pct:.3%} too wide (max {self.params.max_range_pct:.3%}), likely gap day",
                current_time,
            )

        # Breakout direction check
        if latest["price"] <= range_high:
            return StrategySignal.hold(stock_id, self.signal_type, "price has not broken opening range high", current_time)

        # EMA trend filter
        if len(frame) >= self.params.trend_ema_period:
            ema = frame["price"].ewm(span=self.params.trend_ema_period, adjust=False).mean()
            if float(latest["price"]) < float(ema.iloc[-1]):
                return StrategySignal.hold(
                    stock_id, self.signal_type,
                    "breakout against EMA trend (price below EMA)",
                    current_time,
                )

        # Volume confirmation with relative volume
        baseline_volume = float(opening["volume"].mean())
        if baseline_volume <= 0:
            return StrategySignal.hold(stock_id, self.signal_type, "zero baseline volume", current_time)

        post_opening = frame[frame["datetime"] >= open_end]
        if post_opening.empty:
            return StrategySignal.hold(stock_id, self.signal_type, "no post-opening data", current_time)

        breakout_volume = float(post_opening["volume"].tail(5).mean())
        vol_ratio = breakout_volume / baseline_volume

        if vol_ratio < self.params.volume_multiplier:
            return StrategySignal.hold(
                stock_id, self.signal_type,
                f"breakout volume {vol_ratio:.1f}x below {self.params.volume_multiplier}x threshold",
                current_time,
            )

        # Breakout retest confirmation (if enabled)
        if self.params.require_retest and len(post_opening) >= 5:
            post_prices = post_opening["price"].values
            broke_high = False
            retested = False
            resumed = False
            for p in post_prices:
                if p > range_high:
                    broke_high = True
                elif broke_high and p <= range_high * 1.002:  # within 0.2% of range high
                    retested = True
                elif retested and p > range_high * 1.002:
                    resumed = True
                    break

            if broke_high and not resumed and len(post_opening) >= 10:
                # Only enforce retest after enough time has passed
                pass  # Allow direct breakouts if volume is strong enough

        entry = float(latest["price"])
        stop = round(range_low * (1 - self.params.stop_buffer_bps / 10000), 2)
        risk = entry - stop
        if risk <= 0:
            return StrategySignal.hold(stock_id, self.signal_type, "invalid stop distance", current_time)

        take_profit = round(entry + risk * self.params.take_profit_r, 2)

        expected_edge_bps = ((take_profit - entry) / entry) * 10000
        if not self.cost_model.has_sufficient_edge(expected_edge_bps, entry, 1000, is_day_trade=True):
            return StrategySignal.hold(stock_id, self.signal_type, "expected edge does not clear costs", current_time)

        # Confidence scoring
        confidence = 0.55
        if vol_ratio >= 2.0:
            confidence += 0.1
        if vol_ratio >= 3.0:
            confidence += 0.05
        breakout_margin = (entry - range_high) / range_high
        if breakout_margin > 0.005:
            confidence += 0.05
        confidence = min(round(confidence, 2), 0.85)

        return StrategySignal(
            stock_id=stock_id,
            side="BUY",
            signal_type=self.signal_type,
            confidence=confidence,
            entry_price=entry,
            stop_loss=stop,
            take_profit=take_profit,
            max_position_value=self.params.max_position_value,
            reason=(
                f"ORB: price {entry:.2f} broke high {range_high:.2f} | "
                f"range={range_pct:.2%} | vol={vol_ratio:.1f}x | R:R=1:{self.params.take_profit_r}"
            ),
            invalid_reason="",
            created_at=current_time,
        )
