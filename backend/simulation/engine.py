"""HIVEMIND Core Simulation Engine (Phase 2 Demographics & Society Version)."""

import uuid

from backend.agents.agent import Agent
from backend.agents.lifecycle import evaluate_daily_mortality
from backend.agents.personality import generate_personality
from backend.agents.roles import RoleType
from backend.app.config import SimulationConfig
from backend.events.event_bus import EventBus
from backend.events.event_store import EventStore
from backend.events.event_types import Event, create_event
from backend.persistence.db import create_db_engine_and_factory
from backend.simulation.clock import SimulationClock
from backend.simulation.districts import initialize_districts
from backend.simulation.rng import SeededRNG
from backend.simulation.state import WorldState
from backend.society.households import create_household
from backend.society.relationships import RelationType


class SimulationEngine:
    """
    Authoritative simulation orchestrator executing discrete daily ticks.
    Guarantees deterministic progression, event generation, and periodic snapshotting.
    """

    def __init__(self, config: SimulationConfig | None = None):
        self.config: SimulationConfig = config or SimulationConfig()
        self.run_id: str = self.config.run_id or f"run_{uuid.uuid4().hex[:8]}"

        # Initialize persistence with dedicated DB engine and session factory
        self._db_engine, session_factory = create_db_engine_and_factory(
            self.config.database_url
        )
        self.event_store: EventStore = EventStore(session_factory=session_factory)
        self.rng: SeededRNG = SeededRNG(self.config.seed)
        self.event_bus: EventBus = EventBus()

        # Build initial world state
        self.state: WorldState = WorldState(
            run_id=self.run_id,
            seed=self.config.seed,
            clock=SimulationClock(current_tick=0),
            districts=initialize_districts(),
            agents={},
            households={},
        )

        self._initialize_simulation()

    def _initialize_simulation(self) -> None:
        """Populate initial agents, households, roles, personalities, and persist day 0 baseline."""
        self.event_store.record_run(
            run_id=self.run_id,
            seed=self.config.seed,
            total_days=self.config.total_days,
            name=self.config.city.name,
        )

        init_events: list[Event] = []

        # Deterministic agent population setup
        agent_rng = self.rng.get_stream("agent_init")
        district_ids = list(self.state.districts.keys())

        roles_pool = [
            RoleType.MANUAL_WORKER,
            RoleType.SKILLED_WORKER,
            RoleType.ENGINEER,
            RoleType.TEACHER,
            RoleType.HEALTHCARE_WORKER,
            RoleType.RESEARCHER,
            RoleType.BUSINESS_OWNER,
            RoleType.INVESTOR,
            RoleType.STUDENT,
            RoleType.UNEMPLOYED,
        ]

        created_agents: list[Agent] = []

        for idx in range(1, self.config.city.starting_population + 1):
            agent_id = f"agent_{idx:04d}"
            sex = "M" if agent_rng.random() < 0.5 else "F"

            # Sample age between 18 and 65 years
            age_years = agent_rng.randint(18, 65)
            age_days = int(age_years * 365.25) + agent_rng.randint(0, 364)

            # Assign role based on age
            if age_years < 23 and agent_rng.random() < 0.6:
                role = RoleType.STUDENT
                edu_level = 1
                skill = round(agent_rng.uniform(0.2, 0.4), 2)
            else:
                role = roles_pool[agent_rng.randint(0, len(roles_pool) - 1)]
                edu_level = agent_rng.randint(1, 3)
                skill = round(agent_rng.uniform(0.4, 0.9), 2)

            # Mayor assignment for the first agent
            if idx == 1:
                role = RoleType.MAYOR
                edu_level = 3
                skill = 0.85

            district_id = district_ids[agent_rng.randint(0, len(district_ids) - 1)]
            cash = round(agent_rng.uniform(1500.0, 12000.0), 2)
            health = round(agent_rng.uniform(0.85, 1.0), 4)
            personality = generate_personality(agent_rng)

            agent = Agent(
                id=agent_id,
                age_days=age_days,
                sex=sex,
                role=role,
                personality=personality,
                district_id=district_id,
                cash=cash,
                health=health,
                education_level=edu_level,
                skills=skill,
                alive=True,
            )
            self.state.agents[agent_id] = agent
            created_agents.append(agent)

            evt = create_event(
                run_id=self.run_id,
                tick=0,
                event_type="AgentCreated",
                payload=agent.to_dict(),
            )
            init_events.append(evt)
            self.event_bus.publish(evt)

        # Form initial households (cohabiting pairs / single member households)
        hh_rng = self.rng.get_stream("household_init")
        unassigned_agents = list(created_agents)

        while unassigned_agents:
            head = unassigned_agents.pop(0)
            hh = create_household(
                district_id=head.district_id,
                head_agent_id=head.id,
                initial_cash=head.cash,
            )
            head.household_id = hh.id

            # 40% chance of pairing with another unassigned agent of compatible age
            if unassigned_agents and hh_rng.random() < 0.4:
                partner = unassigned_agents.pop(0)
                partner.district_id = head.district_id
                partner.household_id = hh.id
                hh.add_member(partner.id)
                hh.pooled_cash += partner.cash

                # Add spouse relationship edge in social graph
                self.state.relationships.add_edge(
                    head.id, partner.id, RelationType.SPOUSE, trust=0.9
                )
                self.state.relationships.add_edge(
                    partner.id, head.id, RelationType.SPOUSE, trust=0.9
                )

            self.state.households[hh.id] = hh

            hh_evt = create_event(
                run_id=self.run_id,
                tick=0,
                event_type="HouseholdFormed",
                payload=hh.to_dict(),
            )
            init_events.append(hh_evt)
            self.event_bus.publish(hh_evt)

        # Sync metrics & emit initialization event
        self.state.sync_metrics()

        init_evt = create_event(
            run_id=self.run_id,
            tick=0,
            event_type="SimulationInitialized",
            payload={
                "run_id": self.run_id,
                "seed": self.config.seed,
                "population": len(self.state.agents),
                "households": len(self.state.households),
                "districts": len(self.state.districts),
                "metrics": self.state.metrics.to_dict(),
            },
        )
        init_events.append(init_evt)
        self.event_bus.publish(init_evt)

        # Batch write events and save initial snapshot
        self.event_store.append_events(init_events)
        self._save_snapshot()

    def step(self) -> list[Event]:
        """
        Execute one discrete daily tick (1 tick = 1 day).
        Advances clock, updates demographics, Gompertz-Makeham mortality, metrics, and logs events.
        """
        # 1. Advance discrete calendar clock
        tick = self.state.clock.advance(1)
        day_events: list[Event] = []

        # 2. Demographic aging & actuarial mortality
        demo_rng = self.rng.get_stream("demographics")
        for agent in list(self.state.agents.values()):
            if not agent.alive:
                continue

            agent.age_days += 1

            # Micro-fluctuation in health (bounded in [0.0, 1.0])
            health_delta = demo_rng.uniform(-0.0005, 0.0003)
            agent.health = max(0.0, min(1.0, agent.health + health_delta))

            # Evaluate death using Gompertz-Makeham hazard model
            if agent.health <= 0.0 or evaluate_daily_mortality(
                agent.age_years, agent.health, demo_rng
            ):
                agent.alive = False

                # Handle household membership removal
                if agent.household_id and agent.household_id in self.state.households:
                    hh = self.state.households[agent.household_id]
                    hh.remove_member(agent.id)
                    if hh.size == 0:
                        del self.state.households[hh.id]

                # Purge social graph edges
                self.state.relationships.remove_agent(agent.id)

                evt = create_event(
                    run_id=self.run_id,
                    tick=tick,
                    event_type="AgentDied",
                    payload={
                        "agent_id": agent.id,
                        "age_years": agent.age_years,
                        "role": (
                            agent.role.value
                            if hasattr(agent.role, "value")
                            else str(agent.role)
                        ),
                        "cause": (
                            "natural_mortality"
                            if agent.health > 0.0
                            else "health_exhaustion"
                        ),
                    },
                )
                day_events.append(evt)
                self.event_bus.publish(evt)

        # 3. Recalculate district populations and aggregate city telemetry
        self.state.sync_metrics()

        # 4. Emit day completion event
        day_evt = create_event(
            run_id=self.run_id,
            tick=tick,
            event_type="DayTicked",
            payload={
                "tick": tick,
                "date": self.state.clock.format_date(),
                "metrics": self.state.metrics.to_dict(),
            },
        )
        day_events.append(day_evt)
        self.event_bus.publish(day_evt)

        # 5. Persist events
        self.event_store.append_events(day_events)

        # 6. Periodic snapshotting
        if tick % self.config.snapshot_interval_days == 0:
            self._save_snapshot()

        return day_events

    def run(self, days: int | None = None) -> WorldState:
        """Advance the simulation continuously for the specified number of days."""
        target_days = days if days is not None else self.config.total_days
        for _ in range(target_days):
            self.step()
        return self.state

    def _save_snapshot(self) -> None:
        """Persist current WorldState as a point-in-time snapshot."""
        snapshot_id = f"snap_{self.run_id}_{self.state.clock.current_tick:05d}"
        self.event_store.save_snapshot(
            snapshot_id=snapshot_id,
            run_id=self.run_id,
            tick=self.state.clock.current_tick,
            state_blob=self.state.to_dict(),
        )

    def close(self) -> None:
        """Dispose of the database engine and release open connections."""
        if hasattr(self, "_db_engine") and self._db_engine is not None:
            self._db_engine.dispose()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
