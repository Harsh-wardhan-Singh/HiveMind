"""HIVEMIND Authoritative World State Model."""

from dataclasses import dataclass, field
from typing import Any

from backend.simulation.agent import Agent
from backend.simulation.clock import SimulationClock
from backend.simulation.districts import District, initialize_districts
from backend.simulation.metrics import CityMetrics, calculate_metrics


@dataclass
class WorldState:
    run_id: str
    seed: int
    clock: SimulationClock = field(default_factory=SimulationClock)
    districts: dict[str, District] = field(default_factory=initialize_districts)
    agents: dict[str, Agent] = field(default_factory=dict)
    metrics: CityMetrics = field(default_factory=CityMetrics)
    active_policies: dict[str, Any] = field(default_factory=dict)

    def sync_metrics(self) -> CityMetrics:
        """Update and recalculate population metrics and district population counts."""
        self.metrics = calculate_metrics(self.agents)

        # Reset and recalculate district populations
        for d in self.districts.values():
            d.population = 0
        for a in self.agents.values():
            if a.alive and a.district_id in self.districts:
                self.districts[a.district_id].population += 1

        return self.metrics

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "seed": self.seed,
            "tick": self.clock.current_tick,
            "districts": {k: d.to_dict() for k, d in self.districts.items()},
            "agent_count": len(self.agents),
            "metrics": self.metrics.to_dict(),
            "active_policies": self.active_policies,
        }
