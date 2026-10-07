"""Unit tests for Civil Unrest, Riots, Property Damage, Looting & Quelling."""

import random

from backend.agents.agent import Agent
from backend.companies.company import Company
from backend.economy.goods import CommodityType
from backend.politics.government import MunicipalGovernment
from backend.politics.unrest import (
    evaluate_agent_unrest,
    evaluate_district_unrest,
    process_active_riots,
    quell_district_riots,
)
from backend.simulation.districts import District


def test_agent_unrest_calculation():
    # Discontent, starving agent with high neuroticism
    rebel = Agent(
        id="rebel_1",
        age_days=10000,
        district_id="d1",
        cash=10.0,
        health=0.25,
        employer_id=None,
        favorability=0.10,
    )

    unrest_score = evaluate_agent_unrest(
        agent=rebel,
        district_safety=0.30,
        corruption_index=0.20,
    )

    assert unrest_score > 0.40
    assert rebel.unrest > 0.0


def test_district_unrest_and_riot_eruption():
    districts = {
        "d_riot": District(
            id="d_riot",
            name="Slum District",
            land_price=40.0,
            rent=5.0,
            safety_score=0.10,  # Extremely unsafe
            transport_connectivity=0.2,
            housing_units=50,
        )
    }

    # Agents with rock-bottom favorability and high unrest
    agents = {
        f"a_{i}": Agent(
            id=f"a_{i}",
            age_days=10000,
            district_id="d_riot",
            cash=10.0,
            health=0.25,
            employer_id=None,
            favorability=0.05,
            unrest=0.85,
        )
        for i in range(10)
    }

    unrest_scores, new_riots = evaluate_district_unrest(
        districts=districts,
        agents=agents,
        corruption_index=0.25,
        riot_threshold=0.60,
    )

    assert unrest_scores["d_riot"] >= 0.60
    assert "d_riot" in new_riots
    assert districts["d_riot"].is_rioting is True
    assert districts["d_riot"].riot_days == 1


def test_process_active_riots_consequences():
    districts = {
        "d_riot": District(
            id="d_riot",
            name="Riot Zone",
            land_price=100.0,
            rent=10.0,
            safety_score=0.50,
            transport_connectivity=0.5,
            housing_units=100,
            is_rioting=True,
            riot_days=1,
        )
    }
    companies = {
        "c_looted": Company(
            id="c_looted",
            name="Looted Foods",
            district_id="d_riot",
            commodity_type=CommodityType.FOOD,
            inventory=200.0,
            solvency=True,
        )
    }
    agents = {
        "a_rioter": Agent(
            id="a_rioter",
            age_days=10000,
            district_id="d_riot",
            cash=50.0,
            health=0.90,
            unrest=0.80,
        )
    }
    govt = MunicipalGovernment(treasury=20_000.0)
    rng = random.Random(42)

    initial_safety = districts["d_riot"].safety_score
    initial_inventory = companies["c_looted"].inventory
    initial_treasury = govt.treasury

    report = process_active_riots(districts, companies, agents, govt, rng)

    # 1. Safety degraded
    assert districts["d_riot"].safety_score < initial_safety
    # 2. Inventory looted
    assert companies["c_looted"].inventory < initial_inventory
    assert report["total_looted_inventory"] > 0.0
    # 3. Municipal property repair costs incurred
    assert govt.treasury < initial_treasury
    assert report["total_municipal_repairs"] == 500.0


def test_quell_district_riots():
    districts = {
        "d_quell": District(
            id="d_quell",
            name="Calmed District",
            land_price=100.0,
            rent=10.0,
            safety_score=0.70,
            transport_connectivity=0.7,
            housing_units=100,
            is_rioting=True,
            riot_days=5,
            unrest_score=0.35,  # Dropped below quell threshold
        )
    }

    quelled = quell_district_riots(districts, quell_threshold=0.45)

    assert "d_quell" in quelled
    assert districts["d_quell"].is_rioting is False
    assert districts["d_quell"].riot_days == 0
