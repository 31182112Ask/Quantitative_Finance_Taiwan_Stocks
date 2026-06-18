from __future__ import annotations

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

TAIPEI_TZ = ZoneInfo("Asia/Taipei")
MARKET_OPEN = time(9, 0)
MARKET_CLOSE = time(13, 30)


def localize_taipei(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=TAIPEI_TZ)
    return value.astimezone(TAIPEI_TZ)


def is_trading_time(value: datetime) -> bool:
    value = localize_taipei(value)
    if value.weekday() >= 5:
        return False
    return MARKET_OPEN <= value.time() <= MARKET_CLOSE


def minutes_after_open(value: datetime) -> int:
    value = localize_taipei(value)
    opened = datetime.combine(value.date(), MARKET_OPEN, TAIPEI_TZ)
    return int((value - opened).total_seconds() // 60)


def minutes_before_close(value: datetime) -> int:
    value = localize_taipei(value)
    closed = datetime.combine(value.date(), MARKET_CLOSE, TAIPEI_TZ)
    return int((closed - value).total_seconds() // 60)


def is_business_day(value: date) -> bool:
    return value.weekday() < 5
