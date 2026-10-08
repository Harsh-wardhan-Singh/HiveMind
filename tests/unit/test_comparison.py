"""Unit tests for Phase 8 Differential Trajectory Analytics Module."""

from backend.analytics.comparison import (
    compare_simulation_runs,
    generate_ascii_delta_table,
    generate_comparison_chart_data,
)
from backend.app.config import CityConfig, SimulationConfig
from backend.simulation.engine import SimulationEngine


def test_compare_simulation_runs_calculates_deltas():
    """Verify trajectory comparison computes metric divergence and tables."""
    db_url = "sqlite:///:memory:"

    config_a = SimulationConfig(
        run_id="run_comp_a",
        seed=100,
        total_days=5,
        snapshot_interval_days=1,
        database_url=db_url,
        city=CityConfig(starting_population=20),
    )

    with SimulationEngine(config_a) as engine_a:
        for _ in range(5):
            engine_a.step()

        # Fork into Branch B at tick 2 with food subsidy
        with engine_a.fork(
            branch_name="Branch B (Subsidy)",
            fork_tick=2,
            branch_run_id="run_comp_b",
            policy_overrides={"FOOD_SUBSIDY": 0.30},
        ) as engine_b:
            # Advance Branch B to tick 5
            for _ in range(3):
                engine_b.step()

            # Compare Run A vs Run B
            analysis = compare_simulation_runs(
                event_store=engine_a.event_store,
                run_id_a="run_comp_a",
                run_id_b="run_comp_b",
            )

            assert analysis.run_id_a == "run_comp_a"
            assert analysis.run_id_b == "run_comp_b"
            assert analysis.fork_tick == 2
            assert analysis.ticks_compared == 4  # Ticks 2, 3, 4, 5
            assert "treasury_balance" in analysis.summaries
            assert "gdp" in analysis.summaries

            # Check ASCII output formatting
            ascii_table = generate_ascii_delta_table(analysis)
            assert "DIFFERENTIAL TRAJECTORY COMPARISON" in ascii_table
            assert "treasury_balance" in ascii_table

            # Check JSON chart data structure
            chart_data = generate_comparison_chart_data(analysis)
            assert "series" in chart_data
            assert "treasury_balance" in chart_data["series"]
            assert len(chart_data["series"]["treasury_balance"]) == 4
