"""Integration test for event store persistence and snapshots."""

from backend.simulation.engine import SimulationEngine


def test_persistence_events_and_snapshots(base_config):
    with SimulationEngine(base_config) as engine:
        event_store = engine.event_store

        # Verify initialization events were persisted
        init_events = event_store.get_events(
            run_id=engine.run_id, start_tick=0, end_tick=0
        )
        assert len(init_events) == 21  # 20 AgentCreated + 1 SimulationInitialized

        # Run for 20 days (snapshot interval is 10 days in base_config)
        engine.run(days=20)

        # Check that events up to day 20 exist in DB
        all_events = event_store.get_events(
            run_id=engine.run_id, start_tick=0, end_tick=20
        )
        assert len(all_events) > 21

        # Check snapshots at tick 0, 10, 20
        snap_0 = event_store.get_latest_snapshot(run_id=engine.run_id, up_to_tick=0)
        assert snap_0 is not None
        assert snap_0["tick"] == 0

        snap_10 = event_store.get_latest_snapshot(run_id=engine.run_id, up_to_tick=10)
        assert snap_10 is not None
        assert snap_10["tick"] == 10

        snap_latest = event_store.get_latest_snapshot(run_id=engine.run_id)
        assert snap_latest is not None
        assert snap_latest["tick"] == 20
        assert snap_latest["state_blob"]["agent_count"] == 20
