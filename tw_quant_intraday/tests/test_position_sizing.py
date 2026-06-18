from src.risk.position_sizing import shares_by_risk


def test_position_sizing_respects_trade_loss_and_position_cap():
    result = shares_by_risk(
        equity=1_000_000,
        entry_price=100,
        stop_loss=96,
        max_trade_loss_pct=0.008,
        max_position_pct=0.10,
    )
    assert result.quantity == 1000
    assert result.amount == 100000
    assert result.risk_amount == 4000


def test_position_sizing_returns_zero_when_stop_is_not_below_entry():
    result = shares_by_risk(1_000_000, 100, 101, 0.008, 0.10)
    assert result.quantity == 0
