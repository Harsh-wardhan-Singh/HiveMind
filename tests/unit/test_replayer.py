"""Unit tests for Phase 8 Event Replayer Module."""

from backend.app.config import CityConfig, SimulationConfig
from backend.persistence.snapshot import clone_world_state
from backend.replay.replayer import EventReplayer, verify_replay_determinism
from backend.simulation.engine import SimulationEngine


def test_replayer_get_events():
    """Verify EventReplayer fetches recorded timeline events correctly."""
    config = SimulationConfig(
        run_id="test_replay_events",
        seed=4242,
        total_days=4,
        database_url="sqlite:///:memory:",
        city=CityConfig(starting_population=15),
    )

    with SimulationEngine(config) as engine:
        for _ in range(3):
            engine.step()

        replayer = EventReplayer(engine.event_store)
        events = replayer.get_timeline_events("test_replay_events")
        assert len(events) > 0
        assert any(e.event_type == "DayTicked" for e in events)


def test_replayer_reconstruct_state_at_tick():
    """Verify state reconstruction from snapshot."""
    config = SimulationConfig(
        run_id="test_reconstruct_snap",
        seed=777,
        total_days=5,
        snapshot_interval_days=2,
        database_url="sqlite:///:memory:",
        city=CityConfig(starting_population=15),
    )

    with SimulationEngine(config) as engine:
        for _ in range(4):
            engine.step()

        replayer = EventReplayer(engine.event_store)
        reconstructed = replayer.reconstruct_state_at_tick(
            "test_reconstruct_snap", target_tick=2
        )

        assert reconstructed is not None
        assert reconstructed.clock.current_tick == 2
        assert len(reconstructed.agents) == len(engine.state.agents)


def test_verify_replay_determinism_parity():
    """Verify parity comparison identifies identical states and catches discrepancies."""
    config = SimulationConfig(
        run_id="test_parity",
        seed=111,
        total_days=2,
        database_url="sqlite:///:memory:",
        city=CityConfig(starting_population=10),
    )

    with SimulationEngine(config) as engine:
        engine.step()
        state_a = engine.state
        state_b = clone_world_state(state_a)

        # Identical clone must pass parity
        is_identical, diffs = verify_replay_determinism(state_a, state_b)
        assert is_identical is True
        assert len(diffs) == 0

        # Inject discrepancy into state_b
        state_b.government.treasury += 50000.0
        is_identical2, diffs2 = verify_replay_determinism(state_a, state_b)
        assert is_identical2 is False
        assert any("Treasury mismatch" in d for d in diffs2)
