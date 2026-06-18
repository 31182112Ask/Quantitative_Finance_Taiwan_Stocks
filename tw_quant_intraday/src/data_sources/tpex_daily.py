from __future__ import annotations

from src.data_sources.twse_daily import LocalDailyCsvSource


class LocalTpexDailyCsvSource(LocalDailyCsvSource):
    """Same schema as TWSE local daily CSV for first-version offline tests."""
