"""Unit tests for Household Consumption and Subsistence Settlement."""

from backend.agents.agent import Agent
from backend.agents.roles import RoleType
from backend.economy.consumption import (
    calculate_household_demands,
    settle_household_consumption,
)
from backend.economy.goods import CommodityType
from backend.society.households import Household


def test_calculate_household_demands():
    # Setup agents
    agent1 = Agent(
        id="a1",
        age_days=10000,
        district_id="dist_0",
        cash=100.0,
        role=RoleType.MANUAL_WORKER,
        health=1.0,
    )
    agent2 = Agent(
        id="a2",
        age_days=7000,
        district_id="dist_0",
        cash=50.0,
        role=RoleType.STUDENT,
        health=0.5,  # Ill
    )
    agents = {"a1": agent1, "a2": agent2}

    household = Household(
        id="hh_1",
        head_agent_id="a1",
        member_agent_ids=["a1", "a2"],
        district_id="dist_0",
        pooled_cash=6000.0,
    )
    households = {"hh_1": household}

    demands = calculate_household_demands(agents, households)

    # 2 members -> food = 2.0
    assert demands[CommodityType.FOOD] == 2.0
    # 1 household -> housing = 1.0
    assert demands[CommodityType.HOUSING] == 1.0
    # 2 members * 0.05 + 1 ill * 0.3 = 0.1 + 0.3 = 0.4
    assert round(demands[CommodityType.HEALTHCARE], 2) == 0.40
    # pooled_cash > 5000 -> consumer goods = 2 * 0.2 = 0.4
    assert round(demands[CommodityType.CONSUMER_GOODS], 2) == 0.40


def test_settle_household_consumption_sufficient_funds():
    agent = Agent(
        id="a1",
        age_days=10000,
        district_id="dist_0",
        cash=100.0,
        role=RoleType.MANUAL_WORKER,
        health=0.90,
    )
    agents = {"a1": agent}
    household = Household(
        id="hh_1",
        head_agent_id="a1",
        member_agent_ids=["a1"],
        district_id="dist_0",
        pooled_cash=500.0,
    )
    households = {"hh_1": household}

    prices = {CommodityType.FOOD: 10.0, CommodityType.HOUSING: 25.0}
    fill_ratios = {CommodityType.FOOD: 1.0, CommodityType.HEALTHCARE: 1.0}

    expenditures = settle_household_consumption(agents, households, prices, fill_ratios)

    # Total due = 1*10 (food) + 25 (rent) + 0.05*30 (health maintenance) = 36.5
    assert expenditures["hh_1"] == 36.5
    assert household.pooled_cash == 500.0 - 36.5
    # Well-nourished agent health increases slightly
    assert agent.health > 0.90


def test_settle_household_consumption_starvation():
    agent = Agent(
        id="a1",
        age_days=10000,
        district_id="dist_0",
        cash=0.0,
        role=RoleType.MANUAL_WORKER,
        health=0.80,
    )
    agents = {"a1": agent}
    household = Household(
        id="hh_1",
        head_agent_id="a1",
        member_agent_ids=["a1"],
        district_id="dist_0",
        pooled_cash=0.0,  # Broke
    )
    households = {"hh_1": household}

    prices = {CommodityType.FOOD: 10.0, CommodityType.HOUSING: 25.0}
    fill_ratios = {CommodityType.FOOD: 1.0, CommodityType.HEALTHCARE: 0.0}

    settle_household_consumption(agents, households, prices, fill_ratios)

    # Health degraded due to 0 funds for food
    assert agent.health < 0.80


def test_settle_household_consumption_healthcare_recovery():
    agent = Agent(
        id="a1",
        age_days=10000,
        district_id="dist_0",
        cash=500.0,
        role=RoleType.MANUAL_WORKER,
        health=0.60,  # Low health
    )
    agents = {"a1": agent}
    household = Household(
        id="hh_1",
        head_agent_id="a1",
        member_agent_ids=["a1"],
        district_id="dist_0",
        pooled_cash=500.0,
    )
    households = {"hh_1": household}

    prices = {CommodityType.FOOD: 10.0, CommodityType.HOUSING: 25.0}
    fill_ratios = {CommodityType.FOOD: 1.0, CommodityType.HEALTHCARE: 1.0}

    settle_household_consumption(agents, households, prices, fill_ratios)

    # Healthcare access restores health for agents under 0.80
    assert agent.health > 0.60
