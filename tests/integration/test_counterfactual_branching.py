"""Integration tests for Phase 8: Counterfactual Timeline Branching and Differential Trajectory Analysis."""

from backend.analytics.comparison import (
    compare_simulation_runs,
    generate_ascii_delta_table,
)
from backend.app.config import CityConfig, SimulationConfig
from backend.politics.policies import PolicyType
from backend.simulation.engine import SimulationEngine


def test_counterfactual_branching_divergence_integration():
    """
    Acceptance Test for Phase 8:
    1. Run baseline simulation to fork tick.
    2. Fork into Branch A (Food Subsidy) and Branch B (Austerity).
    3. Step both branches forward.
    4. Compute and verify differential trajectories and policy divergence.
    """
    db_url = "sqlite:///:memory:"

    base_config = SimulationConfig(
        run_id="run_baseline_parent",
        seed=424242,
        total_days=30,
        snapshot_interval_days=10,
        database_url=db_url,
        city=CityConfig(
            name="Hivemind Branching Test City",
            starting_population=30,
        ),
    )

    with SimulationEngine(base_config) as parent:
        # Step baseline simulation to tick 15
        fork_tick = 15
        for _ in range(fork_tick):
            parent.step()

        assert parent.state.clock.current_tick == fork_tick

        # 1. Fork Branch A: Food Subsidy (Stimulus)
        branch_a = parent.fork(
            branch_name="Branch A: Food Subsidy",
            fork_tick=fork_tick,
            branch_run_id="branch_a_subsidy",
            policy_overrides={"FOOD_SUBSIDY": 0.35, "duration_days": 15},
        )

        # 2. Fork Branch B: Austerity (Deficit Reduction)
        branch_b = parent.fork(
            branch_name="Branch B: Austerity",
            fork_tick=fork_tick,
            branch_run_id="branch_b_austerity",
            policy_overrides={"AUSTERITY": 0.20, "duration_days": 15},
        )

        # Verify initial policy configurations
        assert any(
            p.policy_type == PolicyType.FOOD_SUBSIDY
            for p in branch_a.state.policy_manager.active_policies.values()
        )
        assert any(
            p.policy_type == PolicyType.AUSTERITY
            for p in branch_b.state.policy_manager.active_policies.values()
        )

        # Step both branches forward for 15 additional days (ticks 16 to 30)
        days_to_run = 15
        for _ in range(days_to_run):
            branch_a.step()
            branch_b.step()

        assert branch_a.state.clock.current_tick == 30
        assert branch_b.state.clock.current_tick == 30

        # Comparative analytics between Branch A and Branch B
        analysis = compare_simulation_runs(
            event_store=parent.event_store,
            run_id_a="branch_b_austerity",  # Baseline comparison: Austerity
            run_id_b="branch_a_subsidy",  # Intervention: Subsidy
        )

        assert analysis.fork_tick == fork_tick
        assert analysis.ticks_compared == 16  # Ticks 15 through 30
        assert "treasury_balance" in analysis.summaries

        table_output = generate_ascii_delta_table(analysis)
        assert "DIFFERENTIAL TRAJECTORY COMPARISON" in table_output
        assert "branch_b_austerity" in table_output
        assert "branch_a_subsidy" in table_output

        # Clean up
        branch_a.close()
        branch_b.close()
