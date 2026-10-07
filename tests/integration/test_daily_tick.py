"""Integration test for daily tick execution and engine invariants."""

from backend.simulation.engine import SimulationEngine


def test_engine_initialization(base_config):
    with SimulationEngine(base_config) as engine:
        assert engine.state.clock.current_tick == 0
        assert len(engine.state.agents) == 20
        assert len(engine.state.districts) == 10
        assert engine.state.metrics.total_population == 20
        assert engine.state.metrics.alive_population == 20

        # Ensure district populations sum up to total alive agents
        district_pop_sum = sum(d.population for d in engine.state.districts.values())
        assert district_pop_sum == 20


def test_engine_step(base_config):
    with SimulationEngine(base_config) as engine:
        initial_ages = {a_id: a.age_days for a_id, a in engine.state.agents.items()}

        events = engine.step()
        assert len(events) >= 1
        assert engine.state.clock.current_tick == 1

        # Verify every alive agent aged by 1 day
        for a_id, agent in engine.state.agents.items():
            if agent.alive:
                assert agent.age_days == initial_ages[a_id] + 1
                assert 0.0 <= agent.health <= 1.0
                assert agent.cash >= 0.0


def test_engine_multi_day_run(base_config):
    with SimulationEngine(base_config) as engine:
        state = engine.run(days=15)
        assert state.clock.current_tick == 15
        assert state.metrics.alive_population <= 20
        assert state.metrics.alive_population > 0
