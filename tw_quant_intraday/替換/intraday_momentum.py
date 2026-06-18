from __future__ import annotations

from datetime import datetime

import pandas as pd

from src.features.technical import returns, vwap
from src.features.volatility import atr
from src.market.cost_model import TaiwanStockCostModel
from src.strategies.base import StrategyBase, StrategySignal


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index."""
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period, min_periods=period).mean()
    loss = (-delta.clip(upper=0)).rolling(period, min_periods=period).mean()
    rs = gain / loss.replace(0, pd.NA)
    return 100 - 100 / (1 + rs)


def _volume_ratio(volume: pd.Series, window: int = 20) -> pd.Series:
    """Current volume vs rolling average."""
    baseline = volume.rolling(window, min_periods=1).mean()
    return volume / baseline.replace(0, pd.NA)


class IntradayMomentumStrategy(StrategyBase):
    """Enhanced intraday momentum with RSI filter, volume confirmation,
    and ATR-based dynamic stop-loss.

    Improvements over original:
    - RSI(14) must be between 50-80 to avoid overbought entries
    - Volume must exceed 1.3x rolling 20-period average
    - Stop-loss uses 1.5x ATR instead of fixed 1%
    - Take-profit uses 2.5x ATR for better risk/reward
    - Added momentum persistence check (3 of last 5 bars positive)
    """

    signal_type = "INTRADAY_MOMENTUM"

    def __init__(
        self,
        cost_model: TaiwanStockCostModel | None = None,
        rsi_lower: float = 50.0,
        rsi_upper: float = 80.0,
        volume_multiplier: float = 1.3,
        atr_stop_mult: float = 1.5,
        atr_tp_mult: float = 2.5,
        momentum_lookback: int = 5,
        momentum_min_positive: int = 3,
    ) -> None:
        self.cost_model = cost_model or TaiwanStockCostModel()
        self.rsi_lower = rsi_lower
        self.rsi_upper = rsi_upper
        self.volume_multiplier = volume_multiplier
        self.atr_stop_mult = atr_stop_mult
        self.atr_tp_mult = atr_tp_mult
        self.momentum_lookback = momentum_lookback
        self.momentum_min_positive = momentum_min_positive

    def generate(self, intraday: pd.DataFrame, stock_id: str, current_time: datetime) -> StrategySignal:
        if len(intraday) < 30:
            return StrategySignal.hold(stock_id, self.signal_type, "insufficient intraday rows (need 30+)", current_time)

        frame = intraday.copy().sort_values("datetime")
        frame["vwap"] = vwap(frame)
        frame["ret1"] = returns(frame["price"], 1)
        frame["ret5"] = returns(frame["price"], 5)
        frame["rsi"] = _rsi(frame["price"], 14)
        frame["vol_ratio"] = _volume_ratio(frame["volume"], 20)

        latest = frame.iloc[-1]

        # Core condition: price above VWAP with positive momentum
        if latest["price"] <= latest["vwap"]:
            return StrategySignal.hold(stock_id, self.signal_type, "price is not above VWAP", current_time)

        if latest["ret5"] <= 0:
            return StrategySignal.hold(stock_id, self.signal_type, "5-period return is not positive", current_time)

        # RSI filter: avoid overbought entries
        rsi_val = latest["rsi"]
        if pd.isna(rsi_val):
            return StrategySignal.hold(stock_id, self.signal_type, "RSI not available", current_time)
        if rsi_val < self.rsi_lower:
            return StrategySignal.hold(stock_id, self.signal_type, f"RSI {rsi_val:.1f} below {self.rsi_lower} threshold", current_time)
        if rsi_val > self.rsi_upper:
            return StrategySignal.hold(stock_id, self.signal_type, f"RSI {rsi_val:.1f} above {self.rsi_upper} (overbought)", current_time)

        # Volume confirmation
        vol_ratio = latest["vol_ratio"]
        if pd.isna(vol_ratio) or vol_ratio < self.volume_multiplier:
            return StrategySignal.hold(
                stock_id, self.signal_type,
                f"volume ratio {vol_ratio:.2f}x below {self.volume_multiplier}x threshold",
                current_time,
            )

        # Momentum persistence: at least N of last M bars should be positive
        recent_returns = frame["ret1"].tail(self.momentum_lookback)
        positive_bars = int((recent_returns > 0).sum())
        if positive_bars < self.momentum_min_positive:
            return StrategySignal.hold(
                stock_id, self.signal_type,
                f"only {positive_bars}/{self.momentum_lookback} positive bars (need {self.momentum_min_positive})",
                current_time,
            )

        # ATR-based dynamic stop-loss and take-profit
        entry = float(latest["price"])
        # Use price range as ATR proxy for intraday data
        frame["high_proxy"] = frame["price"].rolling(5).max()
        frame["low_proxy"] = frame["price"].rolling(5).min()
        price_range = float((frame["high_proxy"] - frame["low_proxy"]).tail(14).mean())
        if pd.isna(price_range) or price_range <= 0:
            price_range = entry * 0.01  # fallback 1%

        stop = round(entry - price_range * self.atr_stop_mult, 2)
        take_profit = round(entry + price_range * self.atr_tp_mult, 2)

        # Cost check
        expected_edge_bps = ((take_profit - entry) / entry) * 10000
        if not self.cost_model.has_sufficient_edge(expected_edge_bps, entry, 1000, is_day_trade=True):
            return StrategySignal.hold(stock_id, self.signal_type, "expected edge does not clear costs", current_time)

        confidence = min(0.4 + (positive_bars / self.momentum_lookback) * 0.2 + (vol_ratio - 1) * 0.1, 0.85)

        return StrategySignal(
            stock_id, "BUY", self.signal_type,
            round(confidence, 2),
            entry, stop, take_profit, 100_000,
            f"momentum above VWAP | RSI={rsi_val:.0f} | vol={vol_ratio:.1f}x | {positive_bars}/{self.momentum_lookback} positive bars",
            "", current_time,
        )
