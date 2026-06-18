from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PaperPosition:
    stock_id: str
    quantity: int
    avg_price: float


@dataclass
class PaperAccount:
    cash: float = 1_000_000
    positions: dict[str, PaperPosition] = field(default_factory=dict)
    realized_pnl: float = 0.0

    def buy(self, stock_id: str, price: float, quantity: int, cost: float) -> None:
        total = price * quantity + cost
        if total > self.cash:
            raise ValueError("insufficient paper cash")
        self.cash -= total
        position = self.positions.get(stock_id)
        if position is None:
            self.positions[stock_id] = PaperPosition(stock_id, quantity, price)
            return
        new_quantity = position.quantity + quantity
        position.avg_price = ((position.avg_price * position.quantity) + (price * quantity)) / new_quantity
        position.quantity = new_quantity

    def sell(self, stock_id: str, price: float, quantity: int, cost: float) -> float:
        position = self.positions.get(stock_id)
        if position is None or position.quantity < quantity:
            raise ValueError("insufficient paper position")
        pnl = (price - position.avg_price) * quantity - cost
        self.cash += price * quantity - cost
        self.realized_pnl += pnl
        position.quantity -= quantity
        if position.quantity == 0:
            del self.positions[stock_id]
        return pnl
