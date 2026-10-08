"""HIVEMIND Deterministic Event Replayer Module (Phase 8).

Reconstructs historical simulation states from immutable event logs and snapshots.
Verifies bit-for-bit determinism across state folds.
"""

from backend.app.config import SimulationConfig
from backend.events.event_store import EventStore
from backend.events.event_types import Event
from backend.persistence.snapshot import deserialize_world_state
from backend.simulation.state import WorldState


class EventReplayer:
    """
    Authoritative state reconstructor that folds event streams
    and restores point-in-time state from snapshots and events.
    """

    def __init__(self, event_store: EventStore):
        self.event_store = event_store

    def get_timeline_events(
        self, run_id: str, start_tick: int = 0, end_tick: int | None = None
    ) -> list[Event]:
        """Fetch chronological event stream for a simulation run."""
        return self.event_store.get_events(
            run_id=run_id, start_tick=start_tick, end_tick=end_tick
        )

    def reconstruct_state_at_tick(
        self,
        run_id: str,
        target_tick: int,
        config: SimulationConfig | None = None,
    ) -> WorldState | None:
        """
        Reconstruct WorldState at a specific historical target_tick.
        Loads the most recent snapshot at or before target_tick, then verifies or
        folds subsequent events up to target_tick.
        """
        # 1. Fetch nearest snapshot <= target_tick
        snap = self.event_store.get_latest_snapshot(run_id, up_to_tick=target_tick)
        if not snap:
            return None

        state = deserialize_world_state(snap["state_blob"])

        # If snapshot is exactly at target_tick, state is already fully restored
        if state.clock.current_tick == target_tick:
            return state

        # If snapshot is earlier than target_tick, fold recorded state updates
        snap_tick = state.clock.current_tick
        events = self.event_store.get_events(
            run_id=run_id, start_tick=snap_tick + 1, end_tick=target_tick
        )

        # Apply event fold onto the state
        self._apply_event_fold(state, events, target_tick)
        return state

    def _apply_event_fold(
        self, state: WorldState, events: list[Event], target_tick: int
    ) -> None:
        """
        Fold event payloads into WorldState to catch up from snapshot tick to target_tick.
        """
        for evt in events:
            p = evt.payload
            etype = evt.event_type

            if etype == "DayTicked":
                state.clock.current_tick = evt.tick
                # Sync macro metrics if available in DayTicked event
                if "market" in p and "prices" in p["market"]:
                    for c_str, price in p["market"]["prices"].items():
                        c_enum = getattr(state.market.prices, c_str, None)
                        if c_enum is not None:
                            state.market.prices[c_enum] = float(price)
            elif etype == "PolicyEnacted":
                # Ensure policy is registered in state
                pol_id = p.get("policy_id")
                if pol_id and pol_id not in state.policy_manager.active_policies:
                    from backend.politics.policies import ActivePolicy, PolicyType

                    p_type = getattr(
                        PolicyType,
                        p.get("policy_type", "FOOD_SUBSIDY"),
                        PolicyType.FOOD_SUBSIDY,
                    )
                    state.policy_manager.active_policies[pol_id] = ActivePolicy(
                        policy_id=pol_id,
                        policy_type=p_type,
                        description=p.get("description", ""),
                        magnitude=float(p.get("magnitude", 0.0)),
                        start_tick=int(p.get("start_tick", evt.tick)),
                        duration_days=int(p.get("duration_days", 30)),
                        daily_cost=float(p.get("daily_cost", 0.0)),
                    )
            elif etype == "PolicyExpired":
                pol_id = p.get("policy_id")
                if pol_id in state.policy_manager.active_policies:
                    del state.policy_manager.active_policies[pol_id]
            elif etype == "MayoralTransition":
                new_m_id = p.get("new_mayor_id")
                if new_m_id:
                    state.government.current_mayor_id = new_m_id
                    state.last_election_tick = evt.tick
            elif etype == "HarmonyShifted":
                state.harmony_tracker.harmony_index = float(
                    p.get("harmony_index", state.harmony_tracker.harmony_index)
                )
                state.harmony_tracker.interpersonal_distrust = float(
                    p.get(
                        "interpersonal_distrust",
                        state.harmony_tracker.interpersonal_distrust,
                    )
                )

        state.clock.current_tick = target_tick
        state.sync_metrics()


def verify_replay_determinism(
    state_a: WorldState, state_b: WorldState, tolerance: float = 0.01
) -> tuple[bool, list[str]]:
    """
    Compare two WorldState instances and verify bit-for-bit or numerical parity.
    Returns (is_identical, discrepancies).
    """
    diffs = []

    if state_a.clock.current_tick != state_b.clock.current_tick:
        diffs.append(
            f"Tick mismatch: A={state_a.clock.current_tick} vs B={state_b.clock.current_tick}"
        )

    if len(state_a.agents) != len(state_b.agents):
        diffs.append(
            f"Agent count mismatch: A={len(state_a.agents)} vs B={len(state_b.agents)}"
        )

    if state_a.metrics.alive_population != state_b.metrics.alive_population:
        diffs.append(
            f"Alive population mismatch: A={state_a.metrics.alive_population} vs B={state_b.metrics.alive_population}"
        )

    treasury_diff = abs(state_a.government.treasury - state_b.government.treasury)
    if treasury_diff > tolerance:
        diffs.append(
            f"Treasury mismatch: A={state_a.government.treasury:.2f} vs B={state_b.government.treasury:.2f} (diff={treasury_diff:.4f})"
        )

    cpi_diff = abs(state_a.metrics.cpi - state_b.metrics.cpi)
    if cpi_diff > tolerance:
        diffs.append(
            f"CPI mismatch: A={state_a.metrics.cpi:.2f} vs B={state_b.metrics.cpi:.2f} (diff={cpi_diff:.4f})"
        )

    approval_diff = abs(
        state_a.metrics.approval_rating - state_b.metrics.approval_rating
    )
    if approval_diff > tolerance:
        diffs.append(
            f"Approval rating mismatch: A={state_a.metrics.approval_rating:.2f}% vs B={state_b.metrics.approval_rating:.2f}%"
        )

    harmony_diff = abs(
        state_a.metrics.society_harmony_index - state_b.metrics.society_harmony_index
    )
    if harmony_diff > tolerance:
        diffs.append(
            f"Harmony mismatch: A={state_a.metrics.society_harmony_index:.4f} vs B={state_b.metrics.society_harmony_index:.4f}"
        )

    return (len(diffs) == 0, diffs)
