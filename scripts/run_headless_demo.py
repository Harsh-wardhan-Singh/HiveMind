"""HIVEMIND Acceptance Demonstration Script (Phases 1-4).

Runs a 100-agent city for 365 days headlessly with full demographic & financial models:
- Demographic: Roles, Big-Five personalities, households, life stages, Gompertz-Makeham mortality.
- Economic: Cobb-Douglas production, Walrasian market clearing, Laspeyres CPI,
  labor matching, payroll settlement, and household subsistence consumption.
- Financial & Banking: Double auction order books, corporate share registry, dividend distributions,
  and Municipal Bank interest-bearing deposits and commercial loans.
"""

import os
import sys
import time

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.config import CityConfig, SimulationConfig
from backend.simulation.engine import SimulationEngine


def run_demo():
    print("=" * 85)
    print(
        " HIVEMIND — MULTI-AGENT CITY: ECONOMY, BANKING & REALPOLITIK (PHASES 1 - 5)"
    )
    print("=" * 85)

    db_path = "hivemind_demo.db"
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except PermissionError:
            pass

    config = SimulationConfig(
        run_id="run_phase5_demo",
        seed=424242,
        total_days=365,
        snapshot_interval_days=30,
        database_url=f"sqlite:///{db_path}",
        city=CityConfig(
            name="Hivemind City (Realpolitik & Governance Baseline)",
            starting_population=100,
        ),
    )

    print(
        f"[*] Configuration: Seed={config.seed}, Days={config.total_days}, "
        f"Population={config.city.starting_population}"
    )
    print(f"[*] Database: {config.database_url}")
    print(
        "[*] Initializing simulation engine with agents, firms, banks, city hall & politics..."
    )

    start_time = time.time()
    with SimulationEngine(config) as engine:
        init_metrics = engine.state.metrics
        print(
            f"[+] Engine Initialized: {len(engine.state.districts)} districts, "
            f"{init_metrics.alive_population} alive agents, {init_metrics.household_count} households, "
            f"{len(engine.state.companies)} companies"
        )
        print(f"    Sitting Mayor:      {engine.state.government.current_mayor_id}")
        print(
            f"    Market Baseline:    CPI={init_metrics.cpi:.2f}, "
            f"Unemployment={init_metrics.unemployment_rate * 100:.1f}%, "
            f"Market Cap={init_metrics.stock_market_cap:,.0f} C"
        )
        print(
            f"    Banking Baseline:   Deposits={init_metrics.total_bank_deposits:,.2f} C, "
            f"Reserves={init_metrics.bank_reserves:,.2f} C"
        )
        print(
            f"    Civic Baseline:     Treasury={init_metrics.treasury_balance:,.2f} C, "
            f"Favorability={init_metrics.city_favorability:.2f}, "
            f"Approval={init_metrics.approval_rating:.1f}%"
        )
        print(
            "[+] Starting 365-day headless multi-agent realpolitik & societal simulation run...\n"
        )

        # Step day by day with periodic logging
        for day in range(1, config.total_days + 1):
            _ = engine.step()
            if day % 60 == 0 or day == 365:
                metrics = engine.state.metrics
                print(
                    f"  Tick {day:03d} | {engine.state.clock.format_date():<14} | "
                    f"Pop: {metrics.alive_population:3d} | "
                    f"Treasury: {metrics.treasury_balance:9.1f} C | "
                    f"Taxes: {metrics.daily_tax_revenue:6.1f} C | "
                    f"Approv: {metrics.approval_rating:5.1f}% | "
                    f"Unrest: {metrics.city_unrest:4.2f} | "
                    f"Riots: {metrics.rioting_districts_count}"
                )

        elapsed = time.time() - start_time
        final_state = engine.state
        event_count = len(engine.event_store.get_events(engine.run_id))

        print("\n" + "=" * 85)
        print(
            " SIMULATION COMPLETE — MACROECONOMIC, BANKING & REALPOLITIK SUMMARY"
        )
        print("=" * 85)
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
        print(f"  Total Currency Volume: {final_state.metrics.total_cash:,.2f} C")
        print(
            f"  Final Unemployment:    {final_state.metrics.unemployment_rate * 100:.2f}%"
        )
        print(f"  Daily GDP Output:      {final_state.metrics.gdp:,.2f} C")
        print(f"  Laspeyres CPI Index:   {final_state.metrics.cpi:.2f}")
        print(f"  Rolling Inflation:     {final_state.metrics.inflation_rate:.2f}%")
        print(f"  Stock Market Cap:      {final_state.metrics.stock_market_cap:,.2f} C")
        print(
            f"  Total Bank Deposits:   {final_state.metrics.total_bank_deposits:,.2f} C"
        )
        print(f"  Bank Cash Reserves:    {final_state.metrics.bank_reserves:,.2f} C")
        print("-" * 85)
        print("  POLITICS, GOVERNANCE & CIVIL UNREST TELEMETRY:")
        print(f"  Sitting Mayor ID:      {final_state.government.current_mayor_id}")
        print(f"  Municipal Treasury:    {final_state.government.treasury:,.2f} C")
        print(f"  Daily Tax Revenue:     {final_state.government.daily_tax_revenue:,.2f} C")
        print(f"  Public Expenditures:   {final_state.government.daily_expenditures:,.2f} C")
        print(f"  Corruption Index:      {final_state.government.corruption_index:.4f}")
        print(f"  Total Embezzled/Graft: {final_state.government.total_embezzled:,.2f} C")
        print(f"  City Favorability:     {final_state.metrics.city_favorability:.4f} [0.0 - 1.0]")
        print(f"  Citizen Approval Rate: {final_state.metrics.approval_rating:.2f}%")
        print(f"  Civil Unrest Index:    {final_state.metrics.city_unrest:.4f} [0.0 - 1.0]")
        print(f"  Rioting Districts:     {final_state.metrics.rioting_districts_count}")
        print(f"  Total Elections Held:  {final_state.government.total_elections_held}")
        print(f"  Active Policies Count: {len(final_state.policy_manager.active_policies)}")
        print("-" * 85)
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
        print("=" * 85)


if __name__ == "__main__":
    run_demo()
