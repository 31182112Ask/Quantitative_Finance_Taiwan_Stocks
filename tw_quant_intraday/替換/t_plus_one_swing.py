from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from src.calendar_tw import localize_taipei
from src.features.technical import moving_average
from src.features.volatility import atr
from src.market.cost_model import TaiwanStockCostModel
from src.strategies.base import StrategyBase, StrategySignal


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period, min_periods=period).mean()
    loss = (-delta.clip(upper=0)).rolling(period, min_periods=period).mean()
    rs = gain / loss.replace(0, pd.NA)
    return 100 - 100 / (1 + rs)


def _macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple[pd.Series, pd.Series]:
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line


@dataclass(frozen=True)
class TPlusOneSwingParams:
    ma_fast: int = 20
    ma_slow: int = 60
    volume_lookback: int = 5
    breakout_lookback: int = 20
    stop_loss_atr_mult: float = 2.0
    take_profit_atr_mult: float = 4.0
    max_position_value: float = 100_000
    rsi_lower: float = 45.0
    rsi_upper: float = 75.0
    min_atr_pct: float = 0.005
    max_atr_pct: float = 0.06


class TPlusOneSwingStrategy(StrategyBase):
    """Enhanced T+1 swing strategy with multi-signal confirmation.

    Improvements over original:
    - RSI(14) filter to avoid overbought entries (45-75 zone)
    - MACD histogram confirmation for trend momentum
    - ATR-based dynamic stop-loss and take-profit instead of fixed %
    - Volatility filter: rejects too-quiet or too-volatile stocks
    - Volume structure: requires 5d avg > 20d avg (not just baseline)
    - Multi-factor confidence scoring
    """

    signal_type = "T_PLUS_ONE_SWING"

    def __init__(
        self,
        params: TPlusOneSwingParams | None = None,
        cost_model: TaiwanStockCostModel | None = None,
    ) -> None:
        self.params = params or TPlusOneSwingParams()
        self.cost_model = cost_model or TaiwanStockCostModel()

    def generate(self, daily: pd.DataFrame, stock_id: str, current_time: datetime) -> StrategySignal:
        current_time = localize_taipei(current_time)
        stock = daily[daily["stock_id"].astype(str) == str(stock_id)].copy()
        if len(stock) < self.params.ma_slow + 1:
            return StrategySignal.hold(stock_id, self.signal_type, "insufficient daily history", current_time)

        stock = stock.sort_values("date")
        stock["ma_fast"] = moving_average(stock["close"], self.params.ma_fast)
        stock["ma_slow"] = moving_average(stock["close"], self.params.ma_slow)
        stock["prior_breakout_high"] = stock["high"].shift(1).rolling(self.params.breakout_lookback).max()
        stock["rsi"] = _rsi(stock["close"], 14)
        stock["atr"] = atr(stock, 14)

        macd_line, signal_line = _macd(stock["close"])
        stock["macd_hist"] = macd_line - signal_line

        latest = stock.iloc[-1]

        # Volume structure analysis
        prev_volume_base = stock["volume"].shift(self.params.volume_lookback).rolling(20, min_periods=5).mean().iloc[-1]
        recent_volume = stock["volume"].tail(self.params.volume_lookback).mean()

        # Check indicator availability
        required = ["ma_fast", "ma_slow", "prior_breakout_high", "rsi", "atr"]
        for col in required:
            if pd.isna(latest[col]):
                return StrategySignal.hold(stock_id, self.signal_type, f"insufficient history for {col}", current_time)

        # Core trend condition: price above both MAs
        if latest["close"] <= latest["ma_fast"]:
            return StrategySignal.hold(stock_id, self.signal_type, "close not above fast MA", current_time)
        if latest["close"] <= latest["ma_slow"]:
            return StrategySignal.hold(stock_id, self.signal_type, "close not above slow MA", current_time)

        # MA alignment: fast MA should be above slow MA
        if latest["ma_fast"] <= latest["ma_slow"]:
            return StrategySignal.hold(stock_id, self.signal_type, "MA not in bullish alignment (fast <= slow)", current_time)

        # Volume confirmation
        if recent_volume <= prev_volume_base:
            return StrategySignal.hold(stock_id, self.signal_type, "recent volume not stronger than baseline", current_time)

        # Range breakout
        if latest["close"] <= latest["prior_breakout_high"]:
            return StrategySignal.hold(stock_id, self.signal_type, "close has not broken prior range", current_time)

        # RSI filter: avoid overbought and oversold
        rsi_val = float(latest["rsi"])
        if rsi_val < self.params.rsi_lower:
            return StrategySignal.hold(stock_id, self.signal_type, f"RSI {rsi_val:.1f} too low (below {self.params.rsi_lower})", current_time)
        if rsi_val > self.params.rsi_upper:
            return StrategySignal.hold(stock_id, self.signal_type, f"RSI {rsi_val:.1f} overbought (above {self.params.rsi_upper})", current_time)

        # MACD confirmation: histogram should be positive or rising
        macd_hist = float(latest["macd_hist"])
        prev_macd_hist = float(stock["macd_hist"].iloc[-2]) if len(stock) >= 2 else 0
        macd_rising = macd_hist > prev_macd_hist

        if macd_hist < 0 and not macd_rising:
            return StrategySignal.hold(stock_id, self.signal_type, "MACD histogram negative and not rising", current_time)

        # Volatility filter using ATR
        atr_val = float(latest["atr"])
        atr_pct = atr_val / float(latest["close"])
        if atr_pct < self.params.min_atr_pct:
            return StrategySignal.hold(stock_id, self.signal_type, f"ATR% {atr_pct:.3%} too low, stock too quiet", current_time)
        if atr_pct > self.params.max_atr_pct:
            return StrategySignal.hold(stock_id, self.signal_type, f"ATR% {atr_pct:.3%} too high, too volatile", current_time)

        # ATR-based dynamic stop-loss and take-profit
        entry = float(latest["close"])
        stop = round(entry - atr_val * self.params.stop_loss_atr_mult, 2)
        take_profit = round(entry + atr_val * self.params.take_profit_atr_mult, 2)

        # Ensure minimum stop distance
        if stop >= entry * 0.995:
            stop = round(entry * 0.965, 2)  # fallback 3.5%

        expected_edge_bps = ((take_profit - entry) / entry) * 10000
        if not self.cost_model.has_sufficient_edge(expected_edge_bps, entry, 1000, is_day_trade=False):
            return StrategySignal.hold(stock_id, self.signal_type, "expected edge does not clear costs", current_time)

        # Multi-factor confidence scoring
        vol_ratio = recent_volume / prev_volume_base if prev_volume_base > 0 else 1.0
        breakout_margin = (latest["close"] - latest["prior_breakout_high"]) / latest["prior_breakout_high"]

        confidence = 0.5
        confidence += min(vol_ratio - 1, 0.5) * 0.15  # volume boost
        confidence += min(breakout_margin, 0.03) * 3   # breakout strength
        if macd_hist > 0:
            confidence += 0.05
        if macd_rising:
            confidence += 0.05
        confidence = min(round(confidence, 2), 0.90)

        return StrategySignal(
            stock_id=stock_id,
            stock_name=str(latest.get("stock_name", "")),
            side="BUY",
            signal_type=self.signal_type,
            confidence=confidence,
            entry_price=entry,
            stop_loss=stop,
            take_profit=take_profit,
            max_position_value=self.params.max_position_value,
            reason=(
                f"breakout above {latest['prior_breakout_high']:.2f} | "
                f"RSI={rsi_val:.0f} | ATR={atr_pct:.2%} | "
                f"vol={vol_ratio:.1f}x | MACD {'▲' if macd_rising else '▼'}"
            ),
            invalid_reason="",
            created_at=current_time,
        )
