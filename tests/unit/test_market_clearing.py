"""Unit tests for Walrasian Market Clearing and Cobweb Price Adjustments."""

from backend.companies.company import Company
from backend.economy.goods import CommodityType
from backend.economy.market import (
    clear_commodity_market,
    initialize_market_state,
)


def test_market_clearing_excess_demand_raises_price():
    market = initialize_market_state()
    initial_food_price = market.prices[CommodityType.FOOD]

    companies = {
        "c1": Company(
            id="c1",
            name="Farm",
            district_id="dist_north",
            commodity_type=CommodityType.FOOD,
            inventory=50.0,
        )
    }

    # Demand (200.0) exceeds supply (50.0) -> Price should rise
    demands = {CommodityType.FOOD: 200.0}
    fill_ratios = clear_commodity_market(
        market, companies, demands, lambda_price_speed=0.1
    )

    assert fill_ratios[CommodityType.FOOD] < 1.0
    assert market.prices[CommodityType.FOOD] > initial_food_price


def test_market_clearing_excess_supply_lowers_price():
    market = initialize_market_state()
    initial_food_price = market.prices[CommodityType.FOOD]

    companies = {
        "c1": Company(
            id="c1",
            name="Farm",
            district_id="dist_north",
            commodity_type=CommodityType.FOOD,
            inventory=500.0,
        )
    }

    # Demand (10.0) far below supply (500.0) -> Price should decrease toward min_price
    demands = {CommodityType.FOOD: 10.0}
    fill_ratios = clear_commodity_market(
        market, companies, demands, lambda_price_speed=0.1
    )

    assert fill_ratios[CommodityType.FOOD] == 1.0
    assert market.prices[CommodityType.FOOD] < initial_food_price

