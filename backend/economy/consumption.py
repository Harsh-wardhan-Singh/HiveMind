"""HIVEMIND Household Consumption & Subsistence Settlement Module."""

from backend.agents.agent import Agent
from backend.economy.goods import (
    CommodityType,
)
from backend.society.households import Household


def calculate_household_demands(
    agents: dict[str, Agent],
    households: dict[str, Household],
) -> dict[CommodityType, float]:
    """Calculate aggregate commodity purchase demands across all households."""
    demands: dict[CommodityType, float] = {c: 0.0 for c in CommodityType}

    for hh in households.values():
        living_members = [
            agents[m_id]
            for m_id in hh.member_agent_ids
            if m_id in agents and agents[m_id].alive
        ]
        if not living_members:
            continue

        member_count = len(living_members)

        # 1. Food: 1.0 unit per living member
        demands[CommodityType.FOOD] += member_count * 1.0

        # 2. Housing: 1.0 unit per household
        demands[CommodityType.HOUSING] += 1.0

        # 3. Healthcare: higher if members are injured/ill
        ill_members = sum(1 for a in living_members if a.health < 0.70)
        demands[CommodityType.HEALTHCARE] += member_count * 0.05 + ill_members * 0.3

        # 4. Consumer Goods: based on pooled wealth
        if hh.pooled_cash > 5000.0:
            demands[CommodityType.CONSUMER_GOODS] += member_count * 0.2

    return demands


def settle_household_consumption(
    agents: dict[str, Agent],
    households: dict[str, Household],
    market_prices: dict[CommodityType, float],
    fill_ratios: dict[CommodityType, float],
    food_subsidy_rate: float = 0.0,
) -> dict[str, float]:
    """
    Settle household grocery and rent purchases, deduct pooled cash,
    and apply health penalties/benefits from nutrition and healthcare access.
    Supports municipal food subsidies lowering grocery costs.
    Returns mapping of household_id to total expenditure.
    """
    expenditures: dict[str, float] = {}
    food_fill = fill_ratios.get(CommodityType.FOOD, 1.0)
    health_fill = fill_ratios.get(CommodityType.HEALTHCARE, 1.0)

    raw_food_price = market_prices.get(CommodityType.FOOD, 10.0)
    food_price = max(1.0, raw_food_price * (1.0 - min(0.50, food_subsidy_rate)))
    rent_price = market_prices.get(CommodityType.HOUSING, 25.0)
    health_price = market_prices.get(CommodityType.HEALTHCARE, 30.0)

    for hh_id, hh in households.items():
        living_members = [
            agents[m_id]
            for m_id in hh.member_agent_ids
            if m_id in agents and agents[m_id].alive
        ]
        if not living_members:
            continue

        member_count = len(living_members)

        # Target expenditures
        food_cost = member_count * food_price * food_fill
        rent_cost = rent_price  # daily residence cost
        ill_members = sum(1 for a in living_members if a.health < 0.85)
        health_units = member_count * 0.05 + ill_members * 0.3
        health_cost = health_units * health_price * health_fill
        total_due = food_cost + rent_cost + health_cost

        # Deduct from pooled cash (or individual members' cash if pooled is exhausted)
        if hh.pooled_cash < total_due:
            deficit = total_due - hh.pooled_cash
            for member in living_members:
                contribution = min(deficit, member.cash)
                member.cash -= contribution
                hh.pooled_cash += contribution
                deficit -= contribution
                if deficit <= 0:
                    break

        if hh.pooled_cash >= total_due:
            hh.pooled_cash -= total_due
            paid = total_due
        else:
            # Partial payment / credit stress
            paid = hh.pooled_cash
            hh.pooled_cash = 0.0
            food_fill_actual = paid / total_due if total_due > 0 else 0.0
            food_fill = min(food_fill, food_fill_actual)

        expenditures[hh_id] = paid

        # Apply biological consequences to household members
        for agent in living_members:
            # Nutritional consequences
            if food_fill < 0.8:
                # Starvation health degradation
                starve_penalty = 0.02 * (1.0 - food_fill)
                agent.health = max(0.0, agent.health - starve_penalty)
            elif agent.health < 0.95 and food_fill >= 0.9:
                # Good nourishment recovers slight health
                agent.health = min(1.0, agent.health + 0.002)

            # Healthcare restoration
            if agent.health < 0.85 and health_fill > 0.5:
                agent.health = min(1.0, agent.health + 0.025)

    return expenditures
