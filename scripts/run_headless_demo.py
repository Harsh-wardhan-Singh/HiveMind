"""HIVEMIND Acceptance Demonstration Script (Phases 1-3).

Runs a 100-agent city for 365 days headlessly with full demographic & economic models:
- Demographic: Roles, Big-Five personalities, households, life stages, Gompertz-Makeham mortality.
- Economic: Cobb-Douglas production, Walrasian market clearing, Laspeyres CPI,
  labor matching, payroll settlement, and household subsistence consumption.
"""

import os
import sys
import time

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.config import CityConfig, SimulationConfig
from backend.economy.goods import CommodityType
from backend.simulation.engine import SimulationEngine


def run_demo():
    print("=" * 80)
    print(" HIVEMIND — MULTI-AGENT DEMOGRAPHIC & ECONOMIC SIMULATION (PHASES 1 - 3)")
    print("=" * 80)

    db_path = "hivemind_demo.db"
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except PermissionError:
            pass

    config = SimulationConfig(
        run_id="run_phase3_demo",
        seed=424242,
        total_days=365,
        snapshot_interval_days=30,
        database_url=f"sqlite:///{db_path}",
        city=CityConfig(
            name="Hivemind City (Economic Baseline)",
            starting_population=100,
        ),
    )

    print(
        f"[*] Configuration: Seed={config.seed}, Days={config.total_days}, "
        f"Population={config.city.starting_population}"
    )
    print(f"[*] Database: {config.database_url}")
    print(
        "[*] Initializing simulation engine with agents, firms & commodity markets..."
    )

    start_time = time.time()
    with SimulationEngine(config) as engine:
        init_metrics = engine.state.metrics
        print(
            f"[+] Engine Initialized: {len(engine.state.districts)} districts, "
            f"{init_metrics.alive_population} alive agents, {init_metrics.household_count} households, "
            f"{len(engine.state.companies)} companies"
        )
        print(f"    Roles Distribution: {init_metrics.role_counts}")
        print(f"    Life Stages:        {init_metrics.life_stage_counts}")
        print(
            f"    Market Baseline:    CPI={init_metrics.cpi:.2f}, "
            f"Unemployment={init_metrics.unemployment_rate * 100:.1f}%, "
            f"Avg Wage={init_metrics.average_wage:.2f} C"
        )
        print(
            "[+] Starting 365-day headless demographic & economic simulation run...\n"
        )

        # Step day by day with periodic logging
        for day in range(1, config.total_days + 1):
            _ = engine.step()
            if day % 60 == 0 or day == 365:
                metrics = engine.state.metrics
                prices = engine.state.market.prices
                print(
                    f"  Tick {day:03d} | {engine.state.clock.format_date():<14} | "
                    f"Pop: {metrics.alive_population:3d} | "
                    f"Unemp: {metrics.unemployment_rate * 100:4.1f}% | "
                    f"CPI: {metrics.cpi:6.2f} ({metrics.inflation_rate:+5.1f}%) | "
                    f"GDP: {metrics.gdp:8.1f} C | "
                    f"Food: {prices[CommodityType.FOOD]:5.2f} C | "
                    f"Rent: {prices[CommodityType.HOUSING]:5.2f} C"
                )

        elapsed = time.time() - start_time
        final_state = engine.state
        event_count = len(engine.event_store.get_events(engine.run_id))

        print("\n" + "=" * 80)
        print(" SIMULATION COMPLETE — DEMOGRAPHIC & MACROECONOMIC SUMMARY")
        print("=" * 80)
        print(f"  Total Days Run:        {final_state.clock.current_tick}")
        print(
            f"  Elapsed Time:          {elapsed:.3f} seconds "
            f"({final_state.clock.current_tick / elapsed:.1f} ticks/sec)"
        )
        print(
            f"  Final Population:      {final_state.metrics.alive_population} / {final_state.metrics.total_population}"
        )
        print(f"  Active Households:     {final_state.metrics.household_count}")
        print(f"  Active Companies:      {len(final_state.companies)}")
        print(f"  Average Agent Health:  {final_state.metrics.average_health:.4f}")
        print(
            f"  Average Agent Age:     {final_state.metrics.average_age_years:.2f} years"
        )
        print(f"  Total Currency Volume: {final_state.metrics.total_cash:.2f} C")
        print(
            f"  Final Unemployment:    {final_state.metrics.unemployment_rate * 100:.2f}%"
        )
        print(f"  Average Daily Wage:    {final_state.metrics.average_wage:.2f} C")
        print(f"  Daily GDP Output:      {final_state.metrics.gdp:.2f} C")
        print(f"  Laspeyres CPI Index:   {final_state.metrics.cpi:.2f}")
        print(f"  Rolling Inflation:     {final_state.metrics.inflation_rate:.2f}%")
        print(
            f"  Corporate Profits:     {final_state.metrics.total_corporate_profit:.2f} C"
        )
        print(
            "  Commodity Prices:      "
            + ", ".join(
                f"{k.value}: {v:.2f} C" for k, v in final_state.market.prices.items()
            )
        )
        print(f"  Total Recorded Events: {event_count}")
        print(f"  Database Stored At:    {db_path}")

        # Check latest snapshot
        snap = engine.event_store.get_latest_snapshot(engine.run_id)
        if snap:
            print(
                f"  Latest Snapshot Tick:  {snap['tick']} (ID: {snap['snapshot_id']})"
            )
        print("=" * 80)


if __name__ == "__main__":
    run_demo()
