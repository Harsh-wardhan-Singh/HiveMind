"""Unit tests for Phase 6 Bounded Knowledge & Observation Packets."""

import random

from backend.agents.agent import Agent
from backend.agents.personality import generate_personality
from backend.agents.roles import RoleType
from backend.information.observation import (
    ObservationPacket,
    generate_agent_observation,
    get_agent_information_tier,
)
from backend.simulation.districts import initialize_districts
from backend.simulation.state import WorldState


def test_agent_information_tiers():
    """Verify tier assignment, noise sigmas, and visible district limits."""
    rng = random.Random(42)
    # Elite agent (Mayor)
    mayor = Agent(
        id="a_mayor",
        age_days=15000,
        sex="M",
        role=RoleType.MAYOR,
        personality=generate_personality(rng),
        district_id="dist_central",
        cash=5000.0,
        education_level=3,
    )
    tier, sigma_l, sigma_d, max_dist = get_agent_information_tier(mayor)
    assert tier == "elite"
    assert max_dist == 10
    assert sigma_l < 0.01  # Edu discount applied

    # Professional agent (Engineer)
    eng = Agent(
        id="a_eng",
        age_days=12000,
        sex="F",
        role=RoleType.ENGINEER,
        personality=generate_personality(rng),
        district_id="dist_industrial",
        cash=3000.0,
        education_level=2,
    )
    tier, sigma_l, sigma_d, max_dist = get_agent_information_tier(eng)
    assert tier == "professional"
    assert max_dist == 5

    # Baseline agent (Manual Worker)
    worker = Agent(
        id="a_worker",
        age_days=10000,
        sex="M",
        role=RoleType.MANUAL_WORKER,
        personality=generate_personality(rng),
        district_id="dist_low_income",
        cash=1000.0,
        education_level=1,
    )
    tier, sigma_l, sigma_d, max_dist = get_agent_information_tier(worker)
    assert tier == "baseline"
    assert max_dist == 2
    assert sigma_d > sigma_l


def test_generate_agent_observation_packet():
    """Verify generation of personalized, bounded observation packet."""
    ws = WorldState(run_id="test_run", seed=42, districts=initialize_districts())
    rng = random.Random(123)

    agent = Agent(
        id="agent_001",
        age_days=10000,
        sex="M",
        role=RoleType.MANUAL_WORKER,
        personality=generate_personality(rng),
        district_id="dist_central",
        cash=2500.0,
        health=0.92,
        favorability=0.65,
        unrest=0.15,
        education_level=1,
    )
    ws.agents[agent.id] = agent

    rng = random.Random(123)
    obs = generate_agent_observation(
        agent=agent,
        world_state=ws,
        rng=rng,
        headlines=[{"headline": "Headline 1", "topic": "NEWS"}],
        rumors=[{"topic": "FOOD", "belief": 0.4}],
    )

    assert isinstance(obs, ObservationPacket)
    assert obs.agent_id == "agent_001"
    assert obs.home_district_id == "dist_central"
    assert obs.information_tier == "baseline"

    # Personal ledger exactness
    assert obs.personal_ledger["cash"] == 2500.0
    assert obs.personal_ledger["health"] == 0.92
    assert obs.personal_ledger["favorability"] == 0.65
    assert obs.personal_ledger["unrest"] == 0.15

    # Bounded horizon: baseline sees only 2 districts
    assert len(obs.known_districts) <= 2
    assert "dist_central" in obs.known_districts
    assert len(obs.read_headlines) == 1
    assert len(obs.known_rumors) == 1

    d = obs.to_dict()
    assert d["agent_id"] == "agent_001"
    assert "personal_ledger" in d
    assert "known_districts" in d
