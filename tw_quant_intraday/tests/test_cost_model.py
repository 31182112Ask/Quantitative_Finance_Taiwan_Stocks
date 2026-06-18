from src.market.cost_model import CostConfig, TaiwanStockCostModel


def test_buy_cost_includes_commission_and_market_friction():
    model = TaiwanStockCostModel(CostConfig(commission_min=1))
    cost = model.estimate("BUY", price=100, quantity=1000)
    assert cost.notional == 100000
    assert cost.commission > 0
    assert cost.transaction_tax == 0
    assert cost.total > cost.commission
    assert cost.total_bps > 0


def test_sell_cost_includes_transaction_tax():
    model = TaiwanStockCostModel(CostConfig(commission_min=1))
    sell = model.estimate("SELL", price=100, quantity=1000, is_day_trade=False)
    day_sell = model.estimate("SELL", price=100, quantity=1000, is_day_trade=True)
    assert sell.transaction_tax == 300
    assert day_sell.transaction_tax == 150
    assert sell.total > day_sell.total


def test_expected_edge_must_clear_round_trip_costs_and_margin():
    model = TaiwanStockCostModel(CostConfig(commission_min=1, min_expected_edge_bps=30))
    assert not model.has_sufficient_edge(20, 100, 1000)
    assert model.has_sufficient_edge(120, 100, 1000)
