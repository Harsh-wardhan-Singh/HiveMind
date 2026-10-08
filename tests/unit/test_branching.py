"""Unit tests for Phase 8 Timeline Fork and Branching Module."""

from backend.app.config import CityConfig, SimulationConfig
from backend.branching.fork_engine import ForkEngine
from backend.politics.policies import PolicyType
from backend.simulation.engine import SimulationEngine


def test_fork_from_engine_creates_branch():
    """Verify ForkEngine forks simulation and preserves state and lineage."""
    config = SimulationConfig(
        run_id="parent_sim_01",
        seed=1234,
        total_days=10,
        snapshot_interval_days=2,
        database_url="sqlite:///:memory:",
        city=CityConfig(starting_population=20),
    )

    with SimulationEngine(config) as parent:
        # Run to tick 4
        for _ in range(4):
            parent.step()

        # Fork from tick 4
        branch = parent.fork(
            branch_name="Branch Stimulus",
            branch_run_id="branch_sim_01",
            policy_overrides={"FOOD_SUBSIDY": 0.25},
        )

        assert branch.run_id == "branch_sim_01"
        assert branch.state.run_id == "branch_sim_01"
        assert branch.state.clock.current_tick == 4
        assert len(branch.state.agents) == len(parent.state.agents)

        # Verify policy override is active in branch
        active_pols = branch.state.policy_manager.active_policies
        assert any(
            p.policy_type == PolicyType.FOOD_SUBSIDY for p in active_pols.values()
        )

        # Check lineage record in event store
        run_meta = branch.event_store.get_run("branch_sim_01")
        assert run_meta is not None
        assert run_meta["parent_run_id"] == "parent_sim_01"
        assert run_meta["fork_tick"] == 4
        assert run_meta["name"] == "Branch Stimulus"

        # Check TimelineForked event recorded
        events = branch.event_store.get_events("branch_sim_01")
        assert any(e.event_type == "TimelineForked" for e in events)

        # Advance branch
        branch.step()
        assert branch.state.clock.current_tick == 5
        branch.close()


def test_fork_with_tax_overrides():
    """Verify counterfactual tax schedule overrides are applied."""
    config = SimulationConfig(
        run_id="parent_tax_sim",
        seed=555,
        total_days=5,
        database_url="sqlite:///:memory:",
        city=CityConfig(starting_population=15),
    )

    with SimulationEngine(config) as parent:
        parent.step()

        branch = ForkEngine.fork_from_engine(
            parent_engine=parent,
            fork_tick=1,
            branch_name="High Corporate Tax",
            branch_run_id="branch_tax_01",
            policy_overrides={
                "tax_rates": {"corporate_tax": 0.35, "income_tax_high": 0.40},
                "treasury_grant": 5000.0,
            },
        )

        assert branch.state.government.tax_rates.corporate_tax == 0.35
        assert branch.state.government.tax_rates.income_tax_high == 0.40
        assert branch.state.government.treasury > parent.state.government.treasury
        branch.close()
