"""Unit tests for Municipal Government, Taxation, Public Services & Corruption."""

import random

from backend.agents.agent import Agent
from backend.agents.personality import Personality
from backend.agents.roles import RoleType
from backend.companies.company import Company
from backend.economy.goods import CommodityType
from backend.politics.government import MunicipalGovernment
from backend.simulation.districts import District
from backend.society.households import Household


def test_progressive_tax_brackets():
    govt = MunicipalGovernment()

    # Subsistence daily wage <= 50 -> 0%
    assert govt.calculate_income_tax(30.0) == 0.0
    assert govt.calculate_income_tax(50.0) == 0.0

    # Middle bracket: 50 < wage <= 180 (10% on excess over 50)
    # wage = 100 -> (100 - 50) * 0.10 = 5.0
    assert govt.calculate_income_tax(100.0) == 5.0
    # wage = 180 -> (180 - 50) * 0.10 = 13.0
    assert govt.calculate_income_tax(180.0) == 13.0

    # High bracket: wage > 180 (13.0 + 22% on excess over 180)
    # wage = 280 -> 13.0 + (100 * 0.22) = 35.0
    assert round(govt.calculate_income_tax(280.0), 2) == 35.0


def test_collect_daily_taxes():
    govt = MunicipalGovernment(treasury=10_000.0)
    agents = {
        "a1": Agent(
            id="a1",
            age_days=10000,
            district_id="d1",
            cash=1000.0,
            employer_id="c1",
        ),
        "a2": Agent(
            id="a2",
            age_days=10000,
            district_id="d1",
            cash=500.0,
            role=RoleType.MAYOR,
        ),
    }
    companies = {
        "c1": Company(
            id="c1",
            name="Corp 1",
            district_id="d1",
            commodity_type=CommodityType.FOOD,
            target_wage=150.0,
            cash=5000.0,
            daily_profit=200.0,  # 15% tax = 30.0
        )
    }
    households = {
        "hh1": Household(
            id="hh1",
            district_id="d1",
            head_agent_id="a1",
            pooled_cash=2000.0,
            member_agent_ids=["a1", "a2"],
        )
    }
    districts = {
        "d1": District(
            id="d1",
            name="Downtown",
            land_price=200.0,
            rent=20.0,
            safety_score=0.8,
            transport_connectivity=0.8,
            housing_units=100,
        )
    }

    tax_report = govt.collect_daily_taxes(agents, companies, households, districts)

    assert tax_report["total_tax_revenue"] > 0.0
    assert tax_report["corporate_tax"] == 30.0  # 200 * 0.15
    assert companies["c1"].cash == 5000.0 - 30.0
    assert govt.treasury == 10_000.0 + tax_report["total_tax_revenue"]
    assert agents["a1"].last_tax_paid > 0.0


def test_disburse_public_services():
    govt = MunicipalGovernment(treasury=5000.0)
    agents = {
        "m1": Agent(
            id="m1",
            age_days=15000,
            district_id="d1",
            cash=100.0,
            role=RoleType.MAYOR,
            employer_id=None,
        )
    }
    districts = {
        "d1": District(
            id="d1",
            name="Civic Center",
            land_price=150.0,
            rent=15.0,
            safety_score=0.70,
            transport_connectivity=0.7,
            housing_units=50,
        )
    }

    initial_treasury = govt.treasury
    initial_safety = districts["d1"].safety_score
    initial_cash = agents["m1"].cash

    expenditures = govt.disburse_public_services(agents, districts)

    assert expenditures > 0.0
    assert govt.treasury < initial_treasury
    assert agents["m1"].cash > initial_cash
    assert districts["d1"].safety_score >= initial_safety


def test_corruption_leak_and_scandal():
    govt = MunicipalGovernment(treasury=50_000.0, corruption_index=0.20)
    corrupt_mayor = Agent(
        id="m_corrupt",
        age_days=18000,
        district_id="d1",
        cash=5000.0,
        role=RoleType.MAYOR,
        personality=Personality(
            openness=0.5,
            conscientiousness=0.1,  # Low conscientiousness -> high graft
            extraversion=0.5,
            agreeableness=0.3,
            neuroticism=0.5,
            risk_tolerance=0.8,
            social_trust=0.2,
            ambition=0.9,  # High ambition
        ),
    )

    rng = random.Random(42)
    leak, _scandal = govt.process_corruption_leak(rng, corrupt_mayor, current_tick=1)

    assert leak > 0.0
    assert govt.total_embezzled == leak
    assert govt.treasury == 50_000.0 - leak


def test_disburse_welfare():
    govt = MunicipalGovernment(treasury=20_000.0)
    poor_agent = Agent(
        id="poor_1",
        age_days=10000,
        district_id="d1",
        cash=20.0,
    )
    households = {
        "hh_poor": Household(
            id="hh_poor",
            district_id="d1",
            head_agent_id="poor_1",
            pooled_cash=50.0,  # Below threshold
            member_agent_ids=["poor_1"],
        )
    }
    agents = {"poor_1": poor_agent}

    welfare_paid = govt.disburse_welfare(
        households=households,
        agents=agents,
        poverty_threshold=300.0,
        grant_amount=40.0,
    )

    assert welfare_paid == 40.0
    assert households["hh_poor"].pooled_cash == 90.0
    assert poor_agent.public_help_received == 40.0
    assert govt.treasury == 20_000.0 - 40.0
