from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from src.strategies.opening_range_breakout import OpeningRangeBreakoutStrategy


def test_no_intraday_data_does_not_emit_actionable_signal():
    signal = OpeningRangeBreakoutStrategy().generate(
        pd.DataFrame(),
        "2330",
        datetime(2026, 6, 18, 10, 0, tzinfo=ZoneInfo("Asia/Taipei")),
    )
    assert signal.side == "HOLD"
    assert signal.entry_price is None
