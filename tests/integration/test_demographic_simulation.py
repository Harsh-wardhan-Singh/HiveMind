"""Integration tests for Phase 2 Demographic & Societal Simulation."""

from backend.agents.roles import RoleType
from backend.app.config import CityConfig, SimulationConfig
from backend.simulation.engine import SimulationEngine


def test_demographic_initialization(base_config):
    with SimulationEngine(base_config) as engine:
        state = engine.state

        # Check agents initialized with roles and personalities
        assert len(state.agents) == 20
        assert len(state.households) > 0

        mayor_found = False
        roles_set = set()
        for agent in state.agents.values():
            assert agent.sex in ("M", "F")
            assert 0.0 <= agent.personality.openness <= 1.0
            assert 0.0 <= agent.personality.neuroticism <= 1.0
            assert agent.household_id is not None
            assert agent.household_id in state.households
            roles_set.add(agent.role)
            if agent.role == RoleType.MAYOR:
                mayor_found = True

        assert mayor_found
        assert len(roles_set) >= 3

        # Check metrics demographic distributions
        metrics = state.metrics
        assert metrics.household_count == len(state.households)
        assert sum(metrics.role_counts.values()) == metrics.alive_population
        assert sum(metrics.life_stage_counts.values()) == metrics.alive_population


def test_demographic_simulation_aging_and_events(base_config):
    with SimulationEngine(base_config) as engine:
        initial_pop = engine.state.metrics.alive_population

        # Step 60 days
        for _ in range(60):
            engine.step()

        state = engine.state
        assert state.clock.current_tick == 60
        assert state.metrics.alive_population <= initial_pop

        # Verify agents aged
        for agent in state.agents.values():
            if agent.alive:
                assert agent.age_days >= 60

        # Check event store for AgentCreated, HouseholdFormed, and DayTicked
        events = engine.event_store.get_events(engine.run_id)
        event_types = {e.event_type for e in events}
        assert "AgentCreated" in event_types
        assert "HouseholdFormed" in event_types
        assert "DayTicked" in event_types
        assert "SimulationInitialized" in event_types


def test_demographic_strict_determinism(temp_db_url):
    """Two simulation runs with identical seed reproduce exact demographic and household structures."""
    cfg_a = SimulationConfig(
        run_id="demo_seed_a",
        seed=777888,
        total_days=30,
        database_url=temp_db_url,
        city=CityConfig(starting_population=25),
    )
    with SimulationEngine(cfg_a) as engine_a:
        state_a = engine_a.run(days=30)
        agents_a = {a_id: a.to_dict() for a_id, a in state_a.agents.items()}
        households_a = {h_id: h.to_dict() for h_id, h in state_a.households.items()}
        metrics_a = state_a.metrics.to_dict()

    cfg_b = SimulationConfig(
        run_id="demo_seed_b",
        seed=777888,
        total_days=30,
        database_url=temp_db_url,
        city=CityConfig(starting_population=25),
    )
    with SimulationEngine(cfg_b) as engine_b:
        state_b = engine_b.run(days=30)
        agents_b = {a_id: a.to_dict() for a_id, a in state_b.agents.items()}
        households_b = {h_id: h.to_dict() for h_id, h in state_b.households.items()}
        metrics_b = state_b.metrics.to_dict()

    assert metrics_a == metrics_b
    assert len(agents_a) == len(agents_b)
    for a_id, a_data in agents_a.items():
        assert a_data == agents_b[a_id]
    assert len(households_a) == len(households_b)
    for h_id, h_data in households_a.items():
        assert h_data == households_b[h_id]
