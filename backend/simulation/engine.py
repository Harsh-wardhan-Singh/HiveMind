"""HIVEMIND Core Simulation Engine (Phase 1 Kernel)."""

import uuid

from backend.app.config import SimulationConfig
from backend.events.event_bus import EventBus
from backend.events.event_store import EventStore
from backend.events.event_types import Event, create_event
from backend.persistence.db import create_db_engine_and_factory
from backend.simulation.agent import Agent
from backend.simulation.clock import SimulationClock
from backend.simulation.districts import initialize_districts
from backend.simulation.rng import SeededRNG
from backend.simulation.state import WorldState


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
        )

        self._initialize_simulation()

    def _initialize_simulation(self) -> None:
        """Populate initial agents, register run, and persist day 0 baseline."""
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

        for idx in range(1, self.config.city.starting_population + 1):
            agent_id = f"agent_{idx:04d}"
            # Sample initial age between 18 and 65 years in days
            age_years = agent_rng.randint(18, 65)
            age_days = int(age_years * 365.25) + agent_rng.randint(0, 364)
            district_id = district_ids[agent_rng.randint(0, len(district_ids) - 1)]
            cash = round(agent_rng.uniform(1000.0, 10000.0), 2)
            health = round(agent_rng.uniform(0.85, 1.0), 4)

            agent = Agent(
                id=agent_id,
                age_days=age_days,
                district_id=district_id,
                cash=cash,
                health=health,
                alive=True,
            )
            self.state.agents[agent_id] = agent

            evt = create_event(
                run_id=self.run_id,
                tick=0,
                event_type="AgentCreated",
                payload=agent.to_dict(),
            )
            init_events.append(evt)
            self.event_bus.publish(evt)

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
        Advances clock, updates demographics, recalculates metrics, and logs events.
        """
        # 1. Advance discrete calendar clock
        tick = self.state.clock.advance(1)
        day_events: list[Event] = []

        # 2. Deterministic demographic aging and slight baseline health updates
        demo_rng = self.rng.get_stream("demographics")
        for agent in self.state.agents.values():
            if not agent.alive:
                continue

            agent.age_days += 1

            # Micro-fluctuation in health (bounded in [0.0, 1.0])
            health_delta = demo_rng.uniform(-0.0005, 0.0003)
            agent.health = max(0.0, min(1.0, agent.health + health_delta))

            if agent.health <= 0.0:
                agent.alive = False
                evt = create_event(
                    run_id=self.run_id,
                    tick=tick,
                    event_type="AgentDied",
                    payload={
                        "agent_id": agent.id,
                        "reason": "health_exhaustion",
                        "age_years": agent.age_years,
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
