from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Side = Literal["BUY", "SELL"]


@dataclass(frozen=True)
class CostConfig:
    commission_rate: float = 0.001425
    commission_discount: float = 0.6
    commission_min: float = 20.0
    stock_transaction_tax: float = 0.003
    day_trade_transaction_tax: float = 0.0015
    default_slippage_bps: float = 5.0
    default_spread_bps: float = 3.0
    default_latency_bps: float = 2.0
    min_expected_edge_bps: float = 30.0

    @classmethod
    def from_mapping(cls, data: dict) -> "CostConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass(frozen=True)
class CostBreakdown:
    notional: float
    commission: float
    transaction_tax: float
    slippage: float
    spread: float
    latency: float
    total: float
    total_bps: float


class TaiwanStockCostModel:
    def __init__(self, config: CostConfig | None = None) -> None:
        self.config = config or CostConfig()

    def estimate(
        self,
        side: Side,
        price: float,
        quantity: int,
        *,
        is_day_trade: bool = False,
        slippage_bps: float | None = None,
        spread_bps: float | None = None,
        latency_bps: float | None = None,
    ) -> CostBreakdown:
        if price <= 0:
            raise ValueError("price must be positive")
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        if side not in {"BUY", "SELL"}:
            raise ValueError("side must be BUY or SELL")

        notional = price * quantity
        commission = max(
            self.config.commission_min,
            notional * self.config.commission_rate * self.config.commission_discount,
        )
        tax_rate = 0.0
        if side == "SELL":
            tax_rate = (
                self.config.day_trade_transaction_tax
                if is_day_trade
                else self.config.stock_transaction_tax
            )
        transaction_tax = notional * tax_rate
        slippage = notional * ((slippage_bps if slippage_bps is not None else self.config.default_slippage_bps) / 10000)
        spread = notional * ((spread_bps if spread_bps is not None else self.config.default_spread_bps) / 10000)
        latency = notional * ((latency_bps if latency_bps is not None else self.config.default_latency_bps) / 10000)
        total = commission + transaction_tax + slippage + spread + latency
        return CostBreakdown(
            notional=notional,
            commission=commission,
            transaction_tax=transaction_tax,
            slippage=slippage,
            spread=spread,
            latency=latency,
            total=total,
            total_bps=(total / notional) * 10000,
        )

    def round_trip_bps(self, price: float, quantity: int, *, is_day_trade: bool = False) -> float:
        buy = self.estimate("BUY", price, quantity, is_day_trade=is_day_trade)
        sell = self.estimate("SELL", price, quantity, is_day_trade=is_day_trade)
        return buy.total_bps + sell.total_bps

    def has_sufficient_edge(
        self,
        expected_edge_bps: float,
        price: float,
        quantity: int,
        *,
        is_day_trade: bool = False,
        safety_margin_bps: float = 5.0,
    ) -> bool:
        required = self.round_trip_bps(price, quantity, is_day_trade=is_day_trade)
        required += self.config.min_expected_edge_bps + safety_margin_bps
        return expected_edge_bps >= required
