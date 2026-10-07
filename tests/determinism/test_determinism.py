"""Strict determinism verification tests for HIVEMIND."""

import gc
import os
import tempfile

from backend.app.config import CityConfig, SimulationConfig
from backend.simulation.engine import SimulationEngine


def test_seed_determinism_reproducibility():
    """Two independent simulation runs initialized with identical seed produce bit-for-bit identical state."""
    seed = 424242
    days = 60
    pop = 50

    fd_a, path_a = tempfile.mkstemp(suffix=".db")
    os.close(fd_a)
    db_a = f"sqlite:///{path_a}"

    fd_b, path_b = tempfile.mkstemp(suffix=".db")
    os.close(fd_b)
    db_b = f"sqlite:///{path_b}"

    try:
        cfg_a = SimulationConfig(
            run_id="run_replica_a",
            seed=seed,
            total_days=days,
            database_url=db_a,
            city=CityConfig(starting_population=pop),
        )
        with SimulationEngine(cfg_a) as engine_a:
            state_a = engine_a.run(days=days)
            events_a = engine_a.event_store.get_events("run_replica_a")

        cfg_b = SimulationConfig(
            run_id="run_replica_b",
            seed=seed,
            total_days=days,
            database_url=db_b,
            city=CityConfig(starting_population=pop),
        )
        with SimulationEngine(cfg_b) as engine_b:
            state_b = engine_b.run(days=days)
            events_b = engine_b.event_store.get_events("run_replica_b")

        # 1. Compare Clock & Metrics
        assert state_a.clock.current_tick == state_b.clock.current_tick
        assert state_a.metrics.to_dict() == state_b.metrics.to_dict()

        # 2. Compare District States
        for d_id in state_a.districts:
            assert (
                state_a.districts[d_id].to_dict() == state_b.districts[d_id].to_dict()
            )

        # 3. Compare Every Agent State
        assert len(state_a.agents) == len(state_b.agents)
        for a_id in state_a.agents:
            agent_a = state_a.agents[a_id].to_dict()
            agent_b = state_b.agents[a_id].to_dict()
            assert agent_a == agent_b

        # 4. Compare Event Sequence Payloads
        assert len(events_a) == len(events_b)
        assert len(events_a) > 0
        for ea, eb in zip(events_a, events_b):
            assert ea.tick == eb.tick
            assert ea.event_type == eb.event_type
            payload_a = {k: v for k, v in ea.payload.items() if k != "run_id"}
            payload_b = {k: v for k, v in eb.payload.items() if k != "run_id"}
            assert payload_a == payload_b

    finally:
        gc.collect()
        for p in [path_a, path_b]:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except PermissionError:
                    pass
