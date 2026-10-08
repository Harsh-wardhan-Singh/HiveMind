"""HIVEMIND Counterfactual Timeline Branch Engine (Phase 8).

Enables point-in-time simulation forks, parent-child lineage tracking,
and policy injection for counterfactual scenario exploration.
"""

import uuid
from dataclasses import dataclass, field
from typing import Any

from backend.app.config import SimulationConfig
from backend.events.event_types import create_event
from backend.persistence.snapshot import clone_world_state, deserialize_world_state
from backend.politics.policies import ActivePolicy, PolicyType
from backend.simulation.engine import SimulationEngine


@dataclass
class BranchMetadata:
    """Lineage and configuration metadata for a forked simulation branch."""

    branch_run_id: str
    parent_run_id: str
    fork_tick: int
    branch_name: str
    policy_overrides: dict[str, Any] = field(default_factory=dict)
    seed: int = 424242
    status: str = "READY"


class ForkEngine:
    """
    Orchestrates creation of counterfactual branch simulations
    from historical or active simulation runs.
    """

    @staticmethod
    def fork_from_engine(
        parent_engine: SimulationEngine,
        fork_tick: int,
        branch_name: str,
        branch_run_id: str | None = None,
        policy_overrides: dict[str, Any] | None = None,
        seed_offset: int = 1000,
    ) -> SimulationEngine:
        """
        Fork a branch directly from an active SimulationEngine.
        If the engine is currently at fork_tick, uses current state;
        otherwise loads snapshot at fork_tick.
        """
        p_run_id = parent_engine.run_id
        b_run_id = branch_run_id or f"{p_run_id}_fork_{uuid.uuid4().hex[:6]}"
        overrides = policy_overrides or {}

        # 1. Obtain state at fork_tick
        if parent_engine.state.clock.current_tick == fork_tick:
            branch_state = clone_world_state(parent_engine.state, new_run_id=b_run_id)
        else:
            snap = parent_engine.event_store.get_snapshot_at_tick(p_run_id, fork_tick)
            if snap and "state_blob" in snap:
                branch_state = deserialize_world_state(
                    snap["state_blob"], new_run_id=b_run_id
                )
            else:
                from backend.replay.replayer import EventReplayer

                replayer = EventReplayer(parent_engine.event_store)
                reconstructed = replayer.reconstruct_state_at_tick(p_run_id, fork_tick)
                if not reconstructed:
                    raise ValueError(
                        f"Cannot fork at tick {fork_tick}: No snapshot or event history found for parent run '{p_run_id}'"
                    )
                branch_state = clone_world_state(reconstructed, new_run_id=b_run_id)

        # 2. Derive branch config
        branch_seed = (
            parent_engine.config.seed + seed_offset
            if seed_offset != 1000
            else parent_engine.config.seed + (abs(hash(b_run_id)) % 50000 + 1)
        )
        branch_config = SimulationConfig(
            run_id=b_run_id,
            seed=branch_seed,
            total_days=parent_engine.config.total_days,
            snapshot_interval_days=parent_engine.config.snapshot_interval_days,
            database_url=parent_engine.config.database_url,
            llm_enabled=parent_engine.config.llm_enabled,
            llm_model=parent_engine.config.llm_model,
            llm_base_url=parent_engine.config.llm_base_url,
            city=parent_engine.config.city,
        )

        # 3. Create branch simulation engine sharing persistence
        branch_engine = SimulationEngine(
            branch_config, event_store=parent_engine.event_store
        )
        branch_state.llm_gateway = branch_engine.llm_gateway
        branch_state.run_id = b_run_id
        branch_engine.state = branch_state

        # 4. Inject counterfactual policy overrides
        ForkEngine._apply_policy_overrides(branch_engine, overrides, fork_tick)

        # 5. Record run metadata in persistence
        branch_engine.event_store.record_run(
            run_id=b_run_id,
            seed=branch_seed,
            total_days=branch_config.total_days,
            name=branch_name,
            parent_run_id=p_run_id,
            fork_tick=fork_tick,
        )

        # 6. Publish TimelineForked event
        fork_evt = create_event(
            run_id=b_run_id,
            tick=fork_tick,
            event_type="TimelineForked",
            payload={
                "parent_run_id": p_run_id,
                "branch_run_id": b_run_id,
                "fork_tick": fork_tick,
                "branch_name": branch_name,
                "policy_overrides": overrides,
                "date": branch_state.clock.format_date(),
            },
        )
        branch_engine.event_store.append_event(fork_evt)
        branch_engine.event_bus.publish(fork_evt)

        # 7. Persist initial branch snapshot at fork point
        branch_engine.save_snapshot()

        return branch_engine

    @staticmethod
    def _apply_policy_overrides(
        engine: SimulationEngine, overrides: dict[str, Any], current_tick: int
    ) -> None:
        """
        Apply counterfactual interventions (e.g. food subsidies, tax adjustments, austerity)
        onto the branched engine's state.
        """
        # Duration for injected policies defaults to remaining duration or 180 days
        duration = int(overrides.get("duration_days", 180))

        # Check for PolicyType interventions
        for key, val in overrides.items():
            key_upper = key.upper()
            pol_enum = getattr(PolicyType, key_upper, None)
            if pol_enum is not None:
                mag = float(val)
                pol_id = f"pol_fork_{key_upper.lower()}"
                active_pol = ActivePolicy(
                    policy_id=pol_id,
                    policy_type=pol_enum,
                    description=f"Counterfactual intervention: {key_upper} (magnitude {mag})",
                    magnitude=mag,
                    start_tick=current_tick,
                    duration_days=duration,
                    daily_cost=(
                        250.0
                        if pol_enum == PolicyType.FOOD_SUBSIDY
                        else (400.0 if pol_enum == PolicyType.PUBLIC_WORKS else 0.0)
                    ),
                )
                engine.state.policy_manager.enact_policy(active_pol)

        # Check for TaxRates overrides
        if "tax_rates" in overrides and isinstance(overrides["tax_rates"], dict):
            tr = overrides["tax_rates"]
            gov_tr = engine.state.government.tax_rates
            if "income_tax_low" in tr:
                gov_tr.income_tax_low = float(tr["income_tax_low"])
            if "income_tax_mid" in tr:
                gov_tr.income_tax_mid = float(tr["income_tax_mid"])
            if "income_tax_high" in tr:
                gov_tr.income_tax_high = float(tr["income_tax_high"])
            if "corporate_tax" in tr:
                gov_tr.corporate_tax = float(tr["corporate_tax"])
            if "property_tax" in tr:
                gov_tr.property_tax = float(tr["property_tax"])

        # Check for treasury grant
        if "treasury_grant" in overrides:
            engine.state.government.treasury += float(overrides["treasury_grant"])

        # Re-sync metrics after policy injections
        engine.state.sync_metrics()
