"""Integration tests for City Governance, Politics, Taxes, Unrest & Determinism."""

from backend.simulation.engine import SimulationEngine


def test_political_system_initialization(base_config):
    with SimulationEngine(base_config) as engine:
        assert engine.state.government.current_mayor_id == "agent_0001"
        assert engine.state.government.treasury > 0.0
        assert engine.state.metrics.city_favorability >= 0.0
        assert engine.state.metrics.approval_rating >= 0.0
        assert engine.state.metrics.current_mayor_id == "agent_0001"


def test_political_multi_day_simulation(base_config):
    with SimulationEngine(base_config) as engine:
        state = engine.run(days=20)

        # Check clock and demographic survival
        assert state.clock.current_tick == 20
        assert state.metrics.alive_population > 0

        # Check governance telemetry
        assert state.government.daily_tax_revenue >= 0.0
        assert state.metrics.treasury_balance > 0.0
        assert 0.0 <= state.metrics.city_favorability <= 1.0
        assert 0.0 <= state.metrics.approval_rating <= 100.0
        assert 0.0 <= state.metrics.city_unrest <= 1.0

        # Check that individual agents have favorability and unrest populated
        alive_agents = [a for a in state.agents.values() if a.alive]
        for a in alive_agents:
            assert 0.0 <= a.favorability <= 1.0
            assert 0.0 <= a.unrest <= 1.0


def test_political_strict_determinism(base_config):
    """Verify bit-for-bit determinism across two identical seeded runs with political engine."""
    config_a = base_config.model_copy(
        update={"seed": 777111, "database_url": "sqlite:///:memory:"}
    )
    config_b = base_config.model_copy(
        update={"seed": 777111, "database_url": "sqlite:///:memory:"}
    )

    with SimulationEngine(config_a) as engine_a:
        state_a = engine_a.run(days=30)

    with SimulationEngine(config_b) as engine_b:
        state_b = engine_b.run(days=30)

    # Invariant assertions
    assert state_a.government.treasury == state_b.government.treasury
    assert state_a.government.daily_tax_revenue == state_b.government.daily_tax_revenue
    assert state_a.government.corruption_index == state_b.government.corruption_index
    assert state_a.metrics.city_favorability == state_b.metrics.city_favorability
    assert state_a.metrics.approval_rating == state_b.metrics.approval_rating
    assert state_a.metrics.city_unrest == state_b.metrics.city_unrest
    assert (
        state_a.metrics.rioting_districts_count
        == state_b.metrics.rioting_districts_count
    )
    assert state_a.government.current_mayor_id == state_b.government.current_mayor_id

    # Check district unrest scores
    for d_id in state_a.districts:
        assert (
            state_a.districts[d_id].unrest_score == state_b.districts[d_id].unrest_score
        )
        assert state_a.districts[d_id].is_rioting == state_b.districts[d_id].is_rioting
