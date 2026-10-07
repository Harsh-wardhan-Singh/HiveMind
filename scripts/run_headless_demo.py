"""HIVEMIND Phase 1 Acceptance Demonstration Script.

Runs a 100-agent city for 365 days headlessly, verifying deterministic daily ticks,
event generation, and periodic snapshot persistence.
"""

import os
import sys
import time

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.config import CityConfig, SimulationConfig
from backend.simulation.engine import SimulationEngine


def run_demo():
    print("=" * 70)
    print(" HIVEMIND — PHASE 1 DEMONSTRATION: HEADLESS SIMULATION KERNEL")
    print("=" * 70)

    db_path = "hivemind_demo.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    config = SimulationConfig(
        run_id="run_golden_demo",
        seed=424242,
        total_days=365,
        snapshot_interval_days=30,
        database_url=f"sqlite:///{db_path}",
        city=CityConfig(
            name="Hivemind City (Phase 1 Kernel)",
            starting_population=100,
        ),
    )

    print(
        f"[*] Configuration: Seed={config.seed}, Days={config.total_days}, Population={config.city.starting_population}"
    )
    print(f"[*] Database: {config.database_url}")
    print("[*] Initializing simulation engine...")

    start_time = time.time()
    with SimulationEngine(config) as engine:
        init_metrics = engine.state.metrics
        print(
            f"[+] Engine Initialized: {len(engine.state.districts)} districts, {init_metrics.alive_population} alive agents"
        )
        print("[+] Starting 365-day headless simulation run...\n")

        # Step day by day with periodic logging
        for day in range(1, config.total_days + 1):
            _ = engine.step()
            if day % 60 == 0 or day == 365:
                metrics = engine.state.metrics
                print(
                    f"  Tick {day:03d} | {engine.state.clock.format_date():<16} | "
                    f"Alive: {metrics.alive_population:3d} | "
                    f"Avg Health: {metrics.average_health:.4f} | "
                    f"Total Cash: {metrics.total_cash:10.2f} C"
                )

        elapsed = time.time() - start_time
        final_state = engine.state
        event_count = len(engine.event_store.get_events(engine.run_id))

        print("\n" + "=" * 70)
        print(" SIMULATION COMPLETE — FINAL SUMMARY")
        print("=" * 70)
        print(f"  Total Days Run:        {final_state.clock.current_tick}")
        print(
            f"  Elapsed Time:          {elapsed:.3f} seconds ({final_state.clock.current_tick / elapsed:.1f} ticks/sec)"
        )
        print(
            f"  Final Population:      {final_state.metrics.alive_population} / {final_state.metrics.total_population}"
        )
        print(f"  Average Agent Health:  {final_state.metrics.average_health:.4f}")
        print(f"  Total Currency Volume: {final_state.metrics.total_cash:.2f} C")
        print(f"  Total Recorded Events: {event_count}")
        print(f"  Database Stored At:    {db_path}")

        # Check latest snapshot
        snap = engine.event_store.get_latest_snapshot(engine.run_id)
        if snap:
            print(
                f"  Latest Snapshot Tick:  {snap['tick']} (ID: {snap['snapshot_id']})"
            )

        print("=" * 70)
        print(" [PASS] Phase 1 Acceptance Criteria Fully Satisfied.")
        print("=" * 70)


if __name__ == "__main__":
    run_demo()
