"""Unit tests for Democratic Elections, Candidates, Balloting & Mayoral Succession."""

import random

from backend.agents.agent import Agent
from backend.agents.roles import RoleType
from backend.politics.elections import (
    apply_election_result,
    conduct_election,
    nominate_candidates,
)
from backend.politics.government import MunicipalGovernment
from backend.simulation.districts import District


def test_nominate_candidates_includes_incumbent_and_challengers():
    sitting_mayor = Agent(
        id="mayor_01",
        age_days=18000,
        district_id="d1",
        cash=10000.0,
        role=RoleType.MAYOR,
    )
    agents = {
        "mayor_01": sitting_mayor,
        "eng_01": Agent(
            id="eng_01",
            age_days=14000,
            district_id="d1",
            cash=5000.0,
            role=RoleType.ENGINEER,
        ),
        "doc_01": Agent(
            id="doc_01",
            age_days=15000,
            district_id="d1",
            cash=6000.0,
            role=RoleType.HEALTHCARE_WORKER,
        ),
        "biz_01": Agent(
            id="biz_01",
            age_days=16000,
            district_id="d1",
            cash=12000.0,
            role=RoleType.BUSINESS_OWNER,
        ),
    }
    govt = MunicipalGovernment(current_mayor_id="mayor_01")
    rng = random.Random(42)

    candidates = nominate_candidates("mayor_01", agents, govt, rng)

    assert len(candidates) >= 2
    incumbents = [c for c in candidates if c.is_incumbent]
    challengers = [c for c in candidates if not c.is_incumbent]
    assert len(incumbents) == 1
    assert incumbents[0].agent_id == "mayor_01"
    assert len(challengers) >= 1


def test_conduct_election_balloting():
    sitting_mayor = Agent(
        id="mayor_01",
        age_days=18000,
        district_id="d1",
        cash=10000.0,
        role=RoleType.MAYOR,
        favorability=0.85,  # High favorability across voters
    )
    agents = {
        "mayor_01": sitting_mayor,
        "voter_1": Agent(
            id="voter_1",
            age_days=10000,
            district_id="d1",
            cash=2000.0,
            favorability=0.90,
        ),
        "voter_2": Agent(
            id="voter_2",
            age_days=12000,
            district_id="d1",
            cash=3000.0,
            favorability=0.80,
        ),
        "challenger_1": Agent(
            id="challenger_1",
            age_days=13000,
            district_id="d1",
            cash=1500.0,
            role=RoleType.TEACHER,
            favorability=0.75,
        ),
    }
    districts = {
        "d1": District(
            id="d1",
            name="District 1",
            land_price=100.0,
            rent=10.0,
            safety_score=0.8,
            transport_connectivity=0.8,
            housing_units=50,
        )
    }
    govt = MunicipalGovernment(current_mayor_id="mayor_01")
    rng = random.Random(42)

    result = conduct_election(agents, districts, govt, current_tick=100, rng=rng)

    assert result.total_votes_cast > 0
    assert result.winner_id in agents
    assert len(result.vote_tallies) >= 2


def test_apply_election_result_power_transition():
    govt = MunicipalGovernment(current_mayor_id="old_mayor")
    agents = {
        "old_mayor": Agent(
            id="old_mayor",
            age_days=18000,
            district_id="d1",
            cash=5000.0,
            role=RoleType.MAYOR,
        ),
        "new_winner": Agent(
            id="new_winner",
            age_days=14000,
            district_id="d1",
            cash=4000.0,
            role=RoleType.TEACHER,
        ),
    }

    from backend.politics.elections import ElectionResult

    result = ElectionResult(
        tick=120,
        winner_id="new_winner",
        winner_name="New Mayor",
        winner_platform="Progressive Welfare & Public Relief",
        is_incumbent_reelected=False,
        total_votes_cast=25,
        vote_tallies={"cand_challenger_1": 15, "cand_incumbent": 10},
        candidates=[
            {
                "agent_id": "new_winner",
                "platform": {
                    "income_tax_mid": 0.12,
                    "corporate_tax": 0.22,
                    "anti_corruption_pledge": 0.80,
                },
            }
        ],
    )

    transferred, _msg = apply_election_result(result, govt, agents)

    assert transferred is True
    assert govt.current_mayor_id == "new_winner"
    assert agents["new_winner"].role == RoleType.MAYOR
    assert agents["old_mayor"].role != RoleType.MAYOR
    assert govt.tax_rates.income_tax_mid == 0.12
    assert govt.tax_rates.corporate_tax == 0.22
    assert govt.total_elections_held == 1
