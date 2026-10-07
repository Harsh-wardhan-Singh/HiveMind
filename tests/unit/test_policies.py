"""Unit tests for Government Intervention Policies & Crisis Response."""

import random

from backend.agents.agent import Agent
from backend.politics.government import MunicipalGovernment
from backend.politics.policies import (
    ActivePolicy,
    PolicyManager,
    PolicyType,
)
from backend.simulation.districts import District


def test_policy_manager_lifecycle():
    pm = PolicyManager()
    pol = ActivePolicy(
        policy_id="test_sub",
        policy_type=PolicyType.FOOD_SUBSIDY,
        description="Food Subsidy",
        magnitude=0.30,
        start_tick=10,
        duration_days=20,
    )

    pm.enact_policy(pol)
    assert len(pm.active_policies) == 1
    assert pm.get_food_subsidy_fraction() == 0.30

    # Before expiration
    assert pol.is_expired(25) is False

    # After expiration (tick 30)
    assert pol.is_expired(30) is True


def test_public_works_employment_policy():
    pm = PolicyManager()
    pol = ActivePolicy(
        policy_id="pol_pw",
        policy_type=PolicyType.PUBLIC_WORKS,
        description="Public works",
        magnitude=25.0,
        start_tick=1,
        duration_days=10,
    )
    pm.enact_policy(pol)

    govt = MunicipalGovernment(treasury=10_000.0)
    unemployed_agent = Agent(
        id="unemp_1",
        age_days=10000,
        district_id="d1",
        cash=50.0,
        employer_id=None,
    )
    agents = {"unemp_1": unemployed_agent}
    districts = {
        "d1": District(
            id="d1",
            name="District 1",
            land_price=100.0,
            rent=10.0,
            safety_score=0.60,
            transport_connectivity=0.6,
            housing_units=50,
        )
    }
    households = {}

    initial_safety = districts["d1"].safety_score
    initial_cash = unemployed_agent.cash

    pm.step_policies(
        current_tick=2,
        government=govt,
        households=households,
        agents=agents,
        districts=districts,
    )

    assert unemployed_agent.cash > initial_cash
    assert districts["d1"].safety_score > initial_safety
    assert govt.daily_public_works_paid > 0.0


def test_anti_corruption_crackdown_policy():
    pm = PolicyManager()
    pol = ActivePolicy(
        policy_id="pol_crackdown",
        policy_type=PolicyType.ANTI_CORRUPTION_CRACKDOWN,
        description="Ethics Audit",
        magnitude=0.50,
        start_tick=1,
        duration_days=10,
    )
    pm.enact_policy(pol)

    govt = MunicipalGovernment(treasury=10_000.0, corruption_index=0.20)
    initial_corruption = govt.corruption_index

    pm.step_policies(
        current_tick=2, government=govt, households={}, agents={}, districts={}
    )

    assert govt.corruption_index < initial_corruption


def test_auto_governance_crisis_response():
    pm = PolicyManager()
    govt = MunicipalGovernment(treasury=25_000.0)
    rng = random.Random(42)

    # Response to food inflation crisis (cpi > 120)
    policies = pm.evaluate_auto_governance(
        government=govt,
        avg_favorability=0.40,
        avg_unrest=0.20,
        rioting_count=0,
        cpi=130.0,
        current_tick=15,
        rng=rng,
    )

    assert any(p.policy_type == PolicyType.FOOD_SUBSIDY for p in policies)
    assert pm.get_food_subsidy_fraction() > 0.0
