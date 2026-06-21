from app.engine import BarAggregator, PaperBroker
from app.models import DecisionAction, Tick


def test_bar_aggregator_rolls_bucket_and_preserves_ohlcv() -> None:
    aggregator = BarAggregator(bucket_seconds=1)
    completed, current = aggregator.update(Tick(ts_ms=1_000, price=100.0, size=100))
    assert completed is None
    assert current.open == 100.0

    completed, current = aggregator.update(Tick(ts_ms=1_500, price=101.0, size=200))
    assert completed is None
    assert current.high == 101.0
    assert current.volume == 300
    assert current.trades == 2

    completed, current = aggregator.update(Tick(ts_ms=2_000, price=99.5, size=500))
    assert completed is not None
    assert completed.close == 101.0
    assert completed.turnover == 30_200.0
    assert current.open == 99.5


def test_paper_broker_round_trip_updates_account() -> None:
    broker = PaperBroker(order_size=1_000, slippage_ticks=0)
    bought, buy_fill = broker.execute(DecisionAction.BUY, 100.0)
    assert bought is True
    assert buy_fill == 100.0
    assert broker.account.position_qty == 1_000

    sold, sell_fill = broker.execute(DecisionAction.SELL, 101.0)
    assert sold is True
    assert sell_fill == 101.0
    assert broker.account.position_qty == 0
    assert broker.account.realized_pnl > 0
    assert broker.account.trades == 2
