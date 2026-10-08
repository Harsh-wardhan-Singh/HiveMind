"""HIVEMIND Phase 8 Acceptance Demonstration: Counterfactual Timeline Branching.

Executes a 100-agent city:
1. Runs baseline timeline to Day 180.
2. Pauses and captures state snapshot.
3. Forks into two divergent branches:
   - Branch A: Food Subsidy & Welfare Stimulus (+35% subsidy)
   - Branch B: Fiscal Austerity & Expenditure Cuts (+20% austerity)
4. Advances both timelines forward to Day 365.
5. Computes and displays differential trajectory matrix (ΔGDP, ΔCPI, ΔTreasury, ΔApproval, ΔUnrest).
"""

import os
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.analytics.comparison import (
    compare_simulation_runs,
    generate_ascii_delta_table,
)
from backend.app.config import CityConfig, SimulationConfig
from backend.simulation.engine import SimulationEngine


def run_counterfactual_demo():
    print("=" * 92)
    print(" HIVEMIND — PHASE 8 COUNTERFACTUAL BRANCHING & TIME-TRAVEL REPLAY DEMO")
    print("=" * 92)

    db_path = "hivemind_branching_demo.db"
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except PermissionError:
            pass

    parent_config = SimulationConfig(
        run_id="run_baseline_timeline",
        seed=424242,
        total_days=365,
        snapshot_interval_days=30,
        database_url=f"sqlite:///{db_path}",
        city=CityConfig(
            name="Hivemind Branching City",
            starting_population=100,
        ),
    )

    fork_tick = 180
    print(
        f"[*] Initializing baseline simulation (Seed={parent_config.seed}, Pop={parent_config.city.starting_population})..."
    )

    start_time = time.time()
    with SimulationEngine(parent_config) as parent:
        print(
            f"[*] Advancing baseline timeline to Day {fork_tick} (Pre-Fork Checkpoint)..."
        )
        for day in range(1, fork_tick + 1):
            parent.step()
            if day % 60 == 0 or day == fork_tick:
                m = parent.state.metrics
                print(
                    f"  Day {day:03d} | Pop: {m.alive_population:3d} | "
                    f"Treasury: {m.treasury_balance:9.1f} C | "
                    f"CPI: {m.cpi:5.2f} | "
                    f"Approv: {m.approval_rating:5.1f}% | "
                    f"Unrest: {m.city_unrest:4.2f}"
                )

        print(f"\n[+] Day {fork_tick} reached. Capturing authoritative snapshot...")
        snap_id = parent.save_snapshot()
        print(f"[+] Snapshot saved: '{snap_id}'")

        print("\n[*] Forking timeline at Day 180 into two counterfactual branches:")
        print("    -> Branch A: Food Subsidy & Relief (+35% Food Subsidy)")
        print("    -> Branch B: Fiscal Austerity (-20% Budget Austerity)")

        branch_a = parent.fork(
            branch_name="Branch A: Food Subsidy Relief",
            fork_tick=fork_tick,
            branch_run_id="branch_a_food_subsidy",
            policy_overrides={"FOOD_SUBSIDY": 0.35, "duration_days": 185},
            seed_offset=1000,
        )

        branch_b = parent.fork(
            branch_name="Branch B: Fiscal Austerity",
            fork_tick=fork_tick,
            branch_run_id="branch_b_fiscal_austerity",
            policy_overrides={
                "AUSTERITY": 0.20,
                "tax_rates": {"corporate_tax": 0.25, "income_tax_high": 0.30},
                "duration_days": 185,
            },
            seed_offset=2000,
        )

        remaining_days = 365 - fork_tick
        print(
            f"\n[*] Stepping both branches concurrently from Day {fork_tick + 1} to Day 365 ({remaining_days} days)..."
        )

        t_sim_start = time.time()
        for day in range(fork_tick + 1, 366):
            branch_a.step()
            branch_b.step()
            if day in (240, 300, 365):
                ma = branch_a.state.metrics
                mb = branch_b.state.metrics
                print(
                    f"  Day {day:03d} | "
                    f"Branch A (Subsidy):   Treasury={ma.treasury_balance:8.1f} C, CPI={ma.cpi:5.2f}, Approv={ma.approval_rating:5.1f}%, Unrest={ma.city_unrest:4.2f}\n"
                    f"          | "
                    f"Branch B (Austerity): Treasury={mb.treasury_balance:8.1f} C, CPI={mb.cpi:5.2f}, Approv={mb.approval_rating:5.1f}%, Unrest={mb.city_unrest:4.2f}"
                )

        elapsed = time.time() - start_time
        sim_elapsed = time.time() - t_sim_start
        print(
            f"\n[+] Both timelines reached Day 365 in {sim_elapsed:.2f}s ({remaining_days * 2 / sim_elapsed:.1f} branch-ticks/sec)!"
        )

        # Perform Differential Trajectory Analysis
        print(
            "\n[*] Computing differential trajectory analytics across divergent futures..."
        )
        analysis = compare_simulation_runs(
            event_store=parent.event_store,
            run_id_a="branch_b_fiscal_austerity",  # Baseline comparison
            run_id_b="branch_a_food_subsidy",  # Intervention branch
        )

        ascii_table = generate_ascii_delta_table(analysis)
        print("\n" + ascii_table)

        print(f"\n[+] Total Elapsed Time: {elapsed:.2f}s")
        print("=" * 92)

        branch_a.close()
        branch_b.close()


if __name__ == "__main__":
    run_counterfactual_demo()
