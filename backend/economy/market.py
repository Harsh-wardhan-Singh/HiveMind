from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from backend.companies.company import Company
from backend.economy.goods import (
    COMMODITY_DEFINITIONS,
    CommodityType,
    get_commodity_definition,
)


@dataclass
class MarketState:
    prices: dict[CommodityType, float] = field(default_factory=dict)
    inventories: dict[CommodityType, float] = field(default_factory=dict)
    demands: dict[CommodityType, float] = field(default_factory=dict)
    sales: dict[CommodityType, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "prices": {k.value: round(v, 2) for k, v in self.prices.items()},
            "inventories": {k.value: round(v, 2) for k, v in self.inventories.items()},
            "demands": {k.value: round(v, 2) for k, v in self.demands.items()},
            "sales": {k.value: round(v, 2) for k, v in self.sales.items()},
        }


def initialize_market_state() -> MarketState:
    """Initialize commodity prices and baseline market states."""
    prices = {
        c_type: c_def.base_price for c_type, c_def in COMMODITY_DEFINITIONS.items()
    }
    inventories = {c_type: 1000.0 for c_type in COMMODITY_DEFINITIONS}
    demands = {c_type: 0.0 for c_type in COMMODITY_DEFINITIONS}
    sales = {c_type: 0.0 for c_type in COMMODITY_DEFINITIONS}
    return MarketState(
        prices=prices,
        inventories=inventories,
        demands=demands,
        sales=sales,
    )


def clear_commodity_market(
    market: MarketState,
    companies: dict[str, Company],
    household_demands: dict[CommodityType, float],
    lambda_price_speed: float = 0.04,
) -> dict[CommodityType, float]:
    """
    Clear daily goods market across all commodities.
    1. Pool available supply from producing companies.
    2. Match aggregate demand vs total available supply.
    3. Update market prices via Walrasian Cobweb dynamics.
    4. Settle sales revenues back to corporate balance sheets.
    5. Apply inventory perishability.
    Returns fill ratio for each commodity [0.0, 1.0].
    """
    fill_ratios: dict[CommodityType, float] = {}

    for c_type in CommodityType:
        c_def = get_commodity_definition(c_type)
        current_price = market.prices.get(c_type, c_def.base_price)

        # 1. Total available inventory from producing companies
        producing_firms = [
            comp
            for comp in companies.values()
            if comp.solvency and comp.commodity_type == c_type
        ]
        total_supply = sum(comp.inventory for comp in producing_firms)
        total_demand = household_demands.get(c_type, 0.0)

        # Reset daily revenue and profit for this cycle
        for comp in producing_firms:
            comp.daily_revenue = 0.0
            comp.daily_profit = -comp.daily_expenses

        market.demands[c_type] = total_demand
        market.inventories[c_type] = total_supply

        # 2. Match supply vs demand
        if total_demand <= 0.0:
            fill_ratio = 1.0
            total_sold = 0.0
        elif total_supply >= total_demand:
            fill_ratio = 1.0
            total_sold = total_demand
        else:
            fill_ratio = total_supply / total_demand if total_demand > 0 else 0.0
            total_sold = total_supply

        market.sales[c_type] = total_sold
        fill_ratios[c_type] = fill_ratio

        # 3. Deduct sold inventories and allocate revenue to firms pro-rata
        if total_supply > 0 and total_sold > 0:
            total_revenue = total_sold * current_price
            for comp in producing_firms:
                fraction = comp.inventory / total_supply
                firm_sold = total_sold * fraction
                firm_rev = total_revenue * fraction
                comp.inventory = max(0.0, comp.inventory - firm_sold)
                comp.cash += firm_rev
                comp.daily_revenue = firm_rev
                comp.daily_profit = comp.daily_revenue - comp.daily_expenses

        # 4. Cobweb Price Adjustment Formula:
        # P_{t+1} = clamp(P_{min}, P_{max}, P_t * (1 + lambda * (D - S) / max(D, S, 1)))
        volume_norm = max(total_demand, total_supply, 1.0)
        excess_ratio = max(-1.0, min(1.0, (total_demand - total_supply) / volume_norm))
        new_price = current_price * (1.0 + lambda_price_speed * excess_ratio)
        bounded_price = max(c_def.min_price, min(c_def.max_price, new_price))
        market.prices[c_type] = round(bounded_price, 4)

        # 5. Apply inventory decay / perishability
        for comp in producing_firms:
            comp.inventory *= 1.0 - c_def.perishability_rate

    return fill_ratios
