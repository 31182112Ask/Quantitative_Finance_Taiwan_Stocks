from __future__ import annotations

import asyncio
import math
import random
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque

from .models import (
    AccountState,
    Bar,
    Decision,
    DecisionAction,
    RunMode,
    Side,
    SignalMarker,
    Tick,
)


class BarAggregator:
    """Aggregates trade ticks into deterministic fixed-width OHLCV bars."""

    def __init__(self, bucket_seconds: int = 1) -> None:
        if bucket_seconds <= 0:
            raise ValueError("bucket_seconds must be positive")
        self.bucket_seconds = bucket_seconds
        self.current: Bar | None = None

    def update(self, tick: Tick) -> tuple[Bar | None, Bar]:
        bucket = (tick.ts_ms // 1000 // self.bucket_seconds) * self.bucket_seconds
        completed: Bar | None = None

        if self.current is None or self.current.time != bucket:
            completed = self.current
            self.current = Bar(
                time=bucket,
                open=tick.price,
                high=tick.price,
                low=tick.price,
                close=tick.price,
                volume=tick.size,
                turnover=tick.price * tick.size,
                trades=1,
            )
        else:
            bar = self.current
            bar.high = max(bar.high, tick.price)
            bar.low = min(bar.low, tick.price)
            bar.close = tick.price
            bar.volume += tick.size
            bar.turnover += tick.price * tick.size
            bar.trades += 1

        return completed, self.current


@dataclass(slots=True)
class IndicatorState:
    fast_ema: float | None = None
    slow_ema: float | None = None
    cumulative_turnover: float = 0.0
    cumulative_volume: int = 0
    previous_fast: float | None = None
    previous_slow: float | None = None

    def update(self, bar: Bar, fast_period: int = 9, slow_period: int = 21) -> None:
        self.previous_fast = self.fast_ema
        self.previous_slow = self.slow_ema
        self.fast_ema = _ema(self.fast_ema, bar.close, fast_period)
        self.slow_ema = _ema(self.slow_ema, bar.close, slow_period)
        self.cumulative_turnover += bar.turnover
        self.cumulative_volume += bar.volume

    @property
    def vwap(self) -> float:
        if not self.cumulative_volume:
            return 0.0
        return self.cumulative_turnover / self.cumulative_volume


class VwapEmaStrategy:
    """Transparent starter strategy for UI and execution-pipeline validation.

    It is deliberately simple and is not presented as a profitable strategy.
    """

    def __init__(self, stop_pct: float = 0.0028, reward_multiple: float = 2.0) -> None:
        self.indicators = IndicatorState()
        self.stop_pct = stop_pct
        self.reward_multiple = reward_multiple

    def evaluate(self, bar: Bar, has_position: bool, avg_price: float) -> Decision:
        self.indicators.update(bar)
        fast = self.indicators.fast_ema or bar.close
        slow = self.indicators.slow_ema or bar.close
        vwap = self.indicators.vwap or bar.close
        prev_fast = self.indicators.previous_fast
        prev_slow = self.indicators.previous_slow

        bullish_cross = (
            prev_fast is not None
            and prev_slow is not None
            and prev_fast <= prev_slow
            and fast > slow
        )
        bearish_cross = (
            prev_fast is not None
            and prev_slow is not None
            and prev_fast >= prev_slow
            and fast < slow
        )

        trend_pass = fast > slow
        vwap_pass = bar.close > vwap
        score = int(trend_pass) * 45 + int(vwap_pass) * 35 + int(bullish_cross) * 20

        entry = bar.close
        stop = entry * (1.0 - self.stop_pct)
        take_profit = entry * (1.0 + self.stop_pct * self.reward_multiple)
        action = DecisionAction.HOLD
        reason = "等待 EMA 交叉与 VWAP 过滤同时成立"

        if not has_position and bullish_cross and vwap_pass:
            action = DecisionAction.BUY
            reason = "EMA9 上穿 EMA21，且价格位于当日 VWAP 上方"
        elif has_position:
            stop_price = avg_price * (1.0 - self.stop_pct)
            target_price = avg_price * (1.0 + self.stop_pct * self.reward_multiple)
            entry, stop, take_profit = avg_price, stop_price, target_price
            if bar.close <= stop_price:
                action = DecisionAction.SELL
                reason = "触发固定风险止损"
            elif bar.close >= target_price:
                action = DecisionAction.SELL
                reason = "触发目标收益止盈"
            elif bearish_cross:
                action = DecisionAction.SELL
                reason = "EMA9 下穿 EMA21，趋势条件失效"
            else:
                score = max(score, 60)
                reason = "持仓管理：等待止损、止盈或趋势反转"

        return Decision(
            time=bar.time,
            action=action,
            reason=reason,
            score=min(score, 100),
            entry=round(entry, 4),
            stop=round(stop, 4),
            take_profit=round(take_profit, 4),
            fast_ema=round(fast, 4),
            slow_ema=round(slow, 4),
            vwap=round(vwap, 4),
        )


def _ema(previous: float | None, value: float, period: int) -> float:
    if previous is None:
        return value
    alpha = 2.0 / (period + 1.0)
    return previous + alpha * (value - previous)


class PaperBroker:
    """Minimal long-only paper broker with explicit fees and ETF sell tax."""

    def __init__(
        self,
        order_size: int = 1_000,
        commission_rate: float = 0.001425 * 0.28,
        etf_sell_tax_rate: float = 0.001,
        slippage_ticks: int = 1,
        tick_size: float = 0.05,
    ) -> None:
        self.order_size = order_size
        self.commission_rate = commission_rate
        self.etf_sell_tax_rate = etf_sell_tax_rate
        self.slippage_ticks = slippage_ticks
        self.tick_size = tick_size
        self.account = AccountState()

    def execute(self, action: DecisionAction, market_price: float) -> tuple[bool, float]:
        if action is DecisionAction.BUY and self.account.position_qty == 0:
            fill = market_price + self.slippage_ticks * self.tick_size
            qty = self.order_size
            gross = fill * qty
            fee = max(1.0, gross * self.commission_rate)
            if gross + fee > self.account.cash:
                return False, fill
            self.account.cash -= gross + fee
            self.account.position_qty = qty
            self.account.avg_price = fill
            self.account.fees += fee
            self.account.trades += 1
            self.account.mark(fill)
            return True, fill

        if action is DecisionAction.SELL and self.account.position_qty > 0:
            fill = market_price - self.slippage_ticks * self.tick_size
            qty = self.account.position_qty
            gross = fill * qty
            fee = max(1.0, gross * self.commission_rate)
            tax = gross * self.etf_sell_tax_rate
            pnl = (fill - self.account.avg_price) * qty - fee - tax
            self.account.cash += gross - fee - tax
            self.account.realized_pnl += pnl
            self.account.fees += fee + tax
            self.account.position_qty = 0
            self.account.avg_price = 0.0
            self.account.trades += 1
            self.account.mark(fill)
            return True, fill

        self.account.mark(market_price)
        return False, market_price


class MarketEngine:
    def __init__(self, symbol: str = "00663L", mode: RunMode = RunMode.PAPER) -> None:
        self.symbol = symbol
        self.mode = mode
        self.aggregator = BarAggregator(bucket_seconds=1)
        self.strategy = VwapEmaStrategy()
        self.broker = PaperBroker()
        self.bars: Deque[Bar] = deque(maxlen=600)
        self.signals: Deque[SignalMarker] = deque(maxlen=100)
        self.last_tick: Tick | None = None
        self.last_decision: Decision | None = None
        self.revision = 0
        self.connected = False
        self._running = False
        self._rng = random.Random(663)
        self._demo_price = 100.0
        self._demo_step = 0

    async def run_demo_feed(self) -> None:
        self._running = True
        self.connected = True
        self._bootstrap_history()
        try:
            while self._running:
                self._demo_step += 1
                cyclical_drift = math.sin(self._demo_step / 42.0) * 0.018
                shock = self._rng.gauss(0.0, 0.025)
                self._demo_price = max(1.0, self._demo_price + cyclical_drift + shock)
                rounded = round(self._demo_price / 0.05) * 0.05
                now_ms = int(time.time() * 1000)
                side = Side.BUY if rounded >= (self.last_tick.price if self.last_tick else rounded) else Side.SELL
                tick = Tick(
                    ts_ms=now_ms,
                    price=round(rounded, 2),
                    size=self._rng.choice((100, 200, 500, 1_000, 2_000)),
                    side=side,
                    bid=round(rounded - 0.05, 2),
                    ask=round(rounded + 0.05, 2),
                )
                self.process_tick(tick)
                await asyncio.sleep(0.08)
        finally:
            self.connected = False

    def stop(self) -> None:
        self._running = False

    def process_tick(self, tick: Tick) -> None:
        self.last_tick = tick
        completed, current = self.aggregator.update(tick)
        if completed is not None:
            self.bars.append(completed)
            decision = self.strategy.evaluate(
                completed,
                has_position=self.broker.account.position_qty > 0,
                avg_price=self.broker.account.avg_price,
            )
            self.last_decision = decision
            executed, fill = self.broker.execute(decision.action, completed.close)
            if executed:
                self.signals.append(
                    SignalMarker(
                        time=completed.time,
                        action=decision.action,
                        price=fill,
                        text=f"{decision.action.value} {fill:.2f}",
                    )
                )
        self.broker.account.mark(current.close)
        self.revision += 1

    def _bootstrap_history(self, bars: int = 180) -> None:
        if self.bars or self.aggregator.current is not None:
            return
        end_second = int(time.time()) - bars
        price = self._demo_price
        for index in range(bars * 4):
            step = index + 1
            price += math.sin(step / 35.0) * 0.012 + self._rng.gauss(0.0, 0.018)
            price = round(price / 0.05) * 0.05
            tick = Tick(
                ts_ms=(end_second * 1000) + index * 250,
                price=round(price, 2),
                size=self._rng.choice((100, 200, 500, 1_000)),
            )
            self.process_tick(tick)
        self._demo_price = price

    def snapshot(self) -> dict[str, object]:
        visible_bars = list(self.bars)
        if self.aggregator.current is not None:
            visible_bars.append(self.aggregator.current)

        last_price = self.last_tick.price if self.last_tick else None
        first_price = visible_bars[0].open if visible_bars else last_price
        change_pct = (
            ((last_price - first_price) / first_price) * 100.0
            if last_price is not None and first_price
            else 0.0
        )
        return {
            "type": "snapshot",
            "revision": self.revision,
            "symbol": self.symbol,
            "mode": self.mode.value,
            "feed": "DEMO_TICK_FEED",
            "connected": self.connected,
            "server_time_ms": int(time.time() * 1000),
            "last_price": last_price,
            "change_pct": round(change_pct, 3),
            "bars": [bar.to_dict() for bar in visible_bars],
            "decision": self.last_decision.to_dict() if self.last_decision else None,
            "signals": [signal.to_dict() for signal in self.signals],
            "account": self.broker.account.to_dict(),
            "latency_ms": 0,
            "live_trading_enabled": False,
        }
