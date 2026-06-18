from __future__ import annotations

from datetime import datetime

import pandas as pd

from src.features.technical import vwap
from src.market.cost_model import TaiwanStockCostModel
from src.strategies.base import StrategyBase, StrategySignal


def _volume_spike(volume: pd.Series, window: int = 20, threshold: float = 2.0) -> pd.Series:
    """Detect volume spikes as ratio vs rolling mean."""
    baseline = volume.rolling(window, min_periods=1).mean()
    return volume / baseline.replace(0, pd.NA)


def _price_acceleration(price: pd.Series, window: int = 5) -> pd.Series:
    """Rate of change of returns - detects deceleration of selling."""
    ret = price.pct_change()
    return ret.diff(window)


class VwapReversionStrategy(StrategyBase):
    """Enhanced VWAP mean-reversion with volume spike detection,
    selling deceleration confirmation, and adaptive deviation thresholds.

    Improvements over original:
    - Adaptive deviation threshold based on intraday volatility
    - Volume spike detection to confirm capitulation/exhaustion
    - Selling deceleration check (price acceleration turning positive)
    - Dynamic stop-loss using recent price range
    - Better confidence scoring based on deviation magnitude
    """

    signal_type = "VWAP_REVERSION"

    def __init__(
        self,
        cost_model: TaiwanStockCostModel | None = None,
        min_deviation_pct: float = -0.012,
        max_deviation_pct: float = -0.05,
        volume_spike_threshold: float = 1.5,
        stop_loss_pct: float = 0.012,
    ) -> None:
        self.cost_model = cost_model or TaiwanStockCostModel()
        self.min_deviation_pct = min_deviation_pct
        self.max_deviation_pct = max_deviation_pct
        self.volume_spike_threshold = volume_spike_threshold
        self.stop_loss_pct = stop_loss_pct

    def generate(self, intraday: pd.DataFrame, stock_id: str, current_time: datetime) -> StrategySignal:
        if len(intraday) < 25:
            return StrategySignal.hold(stock_id, self.signal_type, "insufficient intraday rows (need 25+)", current_time)

        frame = intraday.copy().sort_values("datetime")
        frame["vwap"] = vwap(frame)
        frame["vol_spike"] = _volume_spike(frame["volume"], 20, self.volume_spike_threshold)
        frame["price_accel"] = _price_acceleration(frame["price"], 3)

        latest = frame.iloc[-1]
        vwap_val = float(latest["vwap"])
        price_val = float(latest["price"])

        if vwap_val <= 0:
            return StrategySignal.hold(stock_id, self.signal_type, "invalid VWAP", current_time)

        deviation = (price_val - vwap_val) / vwap_val

        # Adaptive threshold: use intraday volatility to set dynamic deviation
        intraday_vol = frame["price"].pct_change().std()
        adaptive_threshold = max(self.min_deviation_pct, -2.0 * intraday_vol) if not pd.isna(intraday_vol) else self.min_deviation_pct

        if deviation >= adaptive_threshold:
            return StrategySignal.hold(
                stock_id, self.signal_type,
                f"deviation {deviation:.3%} not below threshold {adaptive_threshold:.3%}",
                current_time,
            )

        # Reject if deviation is too extreme (potential crash/news event)
        if deviation < self.max_deviation_pct:
            return StrategySignal.hold(
                stock_id, self.signal_type,
                f"deviation {deviation:.3%} too extreme (below {self.max_deviation_pct:.3%}), potential news event",
                current_time,
            )

        # Volume spike confirmation: want to see exhaustion/capitulation
        vol_spike = latest["vol_spike"]
        if pd.isna(vol_spike) or vol_spike < self.volume_spike_threshold:
            return StrategySignal.hold(
                stock_id, self.signal_type,
                f"no volume spike ({vol_spike:.1f}x < {self.volume_spike_threshold}x)",
                current_time,
            )

        # Selling deceleration: price acceleration should be turning positive
        price_accel = latest["price_accel"]
        if not pd.isna(price_accel) and price_accel < 0:
            return StrategySignal.hold(
                stock_id, self.signal_type,
                "selling still accelerating, wait for deceleration",
                current_time,
            )

        entry = price_val
        # Dynamic stop using recent price range
        recent_range = float(frame["price"].tail(10).max() - frame["price"].tail(10).min())
        stop_distance = max(entry * self.stop_loss_pct, recent_range * 0.5)
        stop = round(entry - stop_distance, 2)

        # Take-profit target: partial reversion to VWAP (80%)
        take_profit = round(entry + (vwap_val - entry) * 0.8, 2)

        expected_edge_bps = ((take_profit - entry) / entry) * 10000
        if not self.cost_model.has_sufficient_edge(expected_edge_bps, entry, 1000, is_day_trade=True):
            return StrategySignal.hold(stock_id, self.signal_type, "expected edge does not clear costs", current_time)

        # Confidence based on deviation magnitude and volume spike
        confidence = min(0.45 + abs(deviation) * 5 + (vol_spike - 1) * 0.05, 0.8)

        return StrategySignal(
            stock_id, "BUY", self.signal_type,
            round(confidence, 2),
            entry, stop, take_profit, 80_000,
            f"VWAP reversion | dev={deviation:.2%} | vol_spike={vol_spike:.1f}x | target={take_profit:.2f}",
            "", current_time,
        )
