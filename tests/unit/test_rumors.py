"""Unit tests for Phase 6 Rumor Network Diffusion, Drift & Personality Propensities."""

import random

from backend.agents.agent import Agent
from backend.agents.personality import Personality, generate_personality
from backend.agents.roles import RoleType
from backend.economy.goods import CommodityType
from backend.information.rumors import (
    Rumor,
    RumorEngine,
    calculate_sharing_chance,
)
from backend.simulation.districts import initialize_districts
from backend.simulation.state import WorldState
from backend.society.relationships import RelationshipGraph, RelationType


def test_personality_sharing_propensity():
    """Verify extraversion, neuroticism, and conscientiousness modulate rumor sharing."""
    rumor = Rumor(
        rumor_id="r1",
        topic="CRISIS",
        headline="Scandal in City Hall",
        intensity=0.90,
        veracity=0.10,  # Highly dubious fake rumor
        origin_tick=1,
    )

    # Agent A: Highly extraverted, neurotic, unconscientious (ideal viral spreader)
    spreader = Agent(
        id="a_spreader",
        age_days=10000,
        sex="M",
        role=RoleType.MANUAL_WORKER,
        personality=Personality(
            extraversion=0.95,
            neuroticism=0.90,
            conscientiousness=0.05,
            openness=0.5,
            agreeableness=0.5,
            risk_tolerance=0.5,
            social_trust=0.5,
            ambition=0.5,
        ),
        district_id="dist_central",
        cash=2000.0,
    )

    # Agent B: Introverted, emotionally stable, highly conscientious (skeptical filter)
    filterer = Agent(
        id="a_filterer",
        age_days=10000,
        sex="F",
        role=RoleType.RESEARCHER,
        personality=Personality(
            extraversion=0.05,
            neuroticism=0.10,
            conscientiousness=0.95,
            openness=0.5,
            agreeableness=0.5,
            risk_tolerance=0.5,
            social_trust=0.5,
            ambition=0.5,
        ),
        district_id="dist_central",
        cash=4000.0,
    )

    prob_spreader = calculate_sharing_chance(spreader, rumor)
    prob_filterer = calculate_sharing_chance(filterer, rumor)

    assert prob_spreader > 0.65
    assert prob_filterer <= 0.15
    assert prob_spreader > prob_filterer


def test_rumor_diffusion_along_edges():
    """Verify rumor spreads across social network graph edges."""
    engine = RumorEngine()
    relationships = RelationshipGraph()
    rng = random.Random(42)

    # Create 3 agents along a chain: 1 -> 2 -> 3
    a1 = Agent(
        id="a1",
        age_days=10000,
        sex="M",
        role=RoleType.MANUAL_WORKER,
        personality=generate_personality(rng),
        district_id="dist_central",
        cash=2000.0,
    )
    a1.personality.extraversion = 0.95
    a1.personality.neuroticism = 0.85

    a2 = Agent(
        id="a2",
        age_days=10000,
        sex="F",
        role=RoleType.MANUAL_WORKER,
        personality=generate_personality(rng),
        district_id="dist_central",
        cash=2000.0,
    )
    a3 = Agent(
        id="a3",
        age_days=10000,
        sex="M",
        role=RoleType.MANUAL_WORKER,
        personality=generate_personality(rng),
        district_id="dist_central",
        cash=2000.0,
    )
    agents = {"a1": a1, "a2": a2, "a3": a3}

    relationships.add_edge("a1", "a2", RelationType.FRIEND, trust=0.80)
    relationships.add_edge("a2", "a3", RelationType.FRIEND, trust=0.80)

    # Spawn rumor seeded only in a1
    engine.spawn_rumor(
        topic="GRAFT",
        headline="Mayor Gravely Involved in Graft",
        intensity=0.85,
        veracity=0.70,
        origin_tick=1,
        initial_carriers=["a1"],
    )

    assert "a1" in engine.agent_beliefs
    assert "a2" not in engine.agent_beliefs

    # Diffuse for several cycles
    diffused_any = False
    for tick in range(1, 15):
        transmissions = engine.diffuse_rumors(
            agents=agents,
            relationships=relationships,
            current_tick=tick,
            rng=rng,
        )
        if transmissions:
            diffused_any = True

    assert diffused_any
    # a2 should now believe the rumor
    assert "a2" in engine.agent_beliefs
    assert engine.agent_beliefs["a2"]["GRAFT"] > 0.0


def test_trigger_contextual_rumors():
    """Verify contextual rumors spawn during economic or political distress."""
    engine = RumorEngine()
    ws = WorldState(run_id="test_run", seed=42, districts=initialize_districts())
    rng = random.Random(42)

    a = Agent(
        id="a1",
        age_days=10000,
        sex="M",
        role=RoleType.MANUAL_WORKER,
        personality=generate_personality(rng),
        district_id="dist_central",
        cash=2000.0,
    )
    ws.agents[a.id] = a
    ws.clock.current_tick = 5

    # Simulate bank loan overhang exceeding reserves
    ws.metrics.total_bank_loans = 50000.0
    ws.metrics.bank_reserves = 10000.0

    # Simulate food price inflation
    ws.market.prices[CommodityType.FOOD] = 15.5

    # Simulate corruption
    ws.government.corruption_index = 0.12

    rng = random.Random(42)
    spawned = engine.trigger_contextual_rumors(ws, rng)

    assert len(spawned) == 3
    topics = {r.topic for r in spawned}
    assert "BANK_INSOLVENCY" in topics
    assert "FOOD_SCARCITY" in topics
    assert "MAYOR_GRAFT" in topics


def test_rumor_expiration():
    """Verify rumors older than 35 ticks expire and are removed."""
    engine = RumorEngine()
    relationships = RelationshipGraph()

    engine.spawn_rumor(
        topic="OLD_RUMOR",
        headline="Old Hearsay",
        intensity=0.5,
        veracity=0.5,
        origin_tick=1,
        initial_carriers=[],
    )
    assert len(engine.active_rumors) == 1

    # Diffuse at tick 40 (> 35 days elapsed)
    engine.diffuse_rumors(
        agents={},
        relationships=relationships,
        current_tick=40,
        rng=random.Random(42),
    )
    assert len(engine.active_rumors) == 0
