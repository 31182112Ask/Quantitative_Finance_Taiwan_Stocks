from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PriceLimit:
    limit_up: float
    limit_down: float


def taiwan_price_limit(previous_close: float, pct: float = 0.10) -> PriceLimit:
    if previous_close <= 0:
        raise ValueError("previous_close must be positive")
    return PriceLimit(
        limit_up=round(previous_close * (1 + pct), 2),
        limit_down=round(previous_close * (1 - pct), 2),
    )


def near_limit_up(price: float, previous_close: float, threshold_bps: float = 30) -> bool:
    limit = taiwan_price_limit(previous_close).limit_up
    return ((limit - price) / previous_close) * 10000 <= threshold_bps
