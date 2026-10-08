"""Unit tests for Phase 8 WorldState Snapshots and Persistence Module."""

from backend.app.config import CityConfig, SimulationConfig
from backend.persistence.snapshot import (
    SnapshotManager,
    clone_world_state,
    deserialize_world_state,
    serialize_world_state,
)
from backend.simulation.engine import SimulationEngine


def test_snapshot_serialization_and_deserialization():
    """Verify complete round-trip serialization of WorldState."""
    config = SimulationConfig(
        run_id="test_snap_roundtrip",
        seed=12345,
        total_days=5,
        database_url="sqlite:///:memory:",
        city=CityConfig(starting_population=20),
    )

    with SimulationEngine(config) as engine:
        # Step 3 days to populate transactions and state changes
        for _ in range(3):
            engine.step()

        original_state = engine.state
        blob = serialize_world_state(original_state)

        assert blob["run_id"] == "test_snap_roundtrip"
        assert blob["tick"] == 3
        assert len(blob["agents"]) == len(original_state.agents)
        assert len(blob["companies"]) == len(original_state.companies)
        assert len(blob["districts"]) == 10
        assert "bank" in blob
        assert "government" in blob
        assert "market" in blob

        # Deserialize into new WorldState
        restored_state = deserialize_world_state(blob, new_run_id="restored_run")
        assert restored_state.run_id == "restored_run"
        assert restored_state.clock.current_tick == 3
        assert len(restored_state.agents) == len(original_state.agents)
        assert len(restored_state.companies) == len(original_state.companies)
        assert len(restored_state.districts) == 10

        # Check numerical equality of key indicators
        assert (
            abs(restored_state.government.treasury - original_state.government.treasury)
            < 0.01
        )
        assert abs(restored_state.metrics.gdp - original_state.metrics.gdp) < 0.01
        assert abs(restored_state.metrics.cpi - original_state.metrics.cpi) < 0.01
        assert (
            abs(
                restored_state.metrics.society_harmony_index
                - original_state.metrics.society_harmony_index
            )
            < 0.01
        )


def test_clone_world_state_decoupling():
    """Verify clone_world_state produces an independent in-memory copy."""
    config = SimulationConfig(
        run_id="test_clone",
        seed=42,
        total_days=2,
        database_url="sqlite:///:memory:",
        city=CityConfig(starting_population=15),
    )

    with SimulationEngine(config) as engine:
        engine.step()
        original_state = engine.state
        cloned_state = clone_world_state(original_state, new_run_id="cloned_test")

        assert cloned_state.run_id == "cloned_test"
        first_agent_id = next(iter(original_state.agents.keys()))

        # Modify cloned agent cash
        cloned_state.agents[first_agent_id].cash += 99999.0
        # Original agent must remain unchanged
        assert (
            original_state.agents[first_agent_id].cash
            != cloned_state.agents[first_agent_id].cash
        )


def test_snapshot_manager_persistence():
    """Verify SnapshotManager saving and loading from EventStore."""
    config = SimulationConfig(
        run_id="test_snap_manager",
        seed=999,
        total_days=2,
        database_url="sqlite:///:memory:",
        city=CityConfig(starting_population=10),
    )

    with SimulationEngine(config) as engine:
        engine.step()
        manager = SnapshotManager(engine.event_store)
        snap_id = manager.save_snapshot(engine.state)

        assert snap_id.startswith("snap_test_snap_manager_")

        loaded_state = manager.load_snapshot("test_snap_manager", tick=1)
        assert loaded_state is not None
        assert loaded_state.clock.current_tick == 1
        assert len(loaded_state.agents) == len(engine.state.agents)

        # Nonexistent tick returns None
        assert manager.load_snapshot("test_snap_manager", tick=999) is None
