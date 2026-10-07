"""HIVEMIND City Metrics Module (Phase 2 Demographics Version)."""

from dataclasses import dataclass, field
from typing import Any

from backend.agents.agent import Agent


@dataclass
class CityMetrics:
    total_population: int = 0
    alive_population: int = 0
    average_health: float = 0.0
    average_cash: float = 0.0
    total_cash: float = 0.0
    average_age_years: float = 0.0
    household_count: int = 0
    life_stage_counts: dict[str, int] = field(default_factory=dict)
    role_counts: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_population": self.total_population,
            "alive_population": self.alive_population,
            "average_health": round(self.average_health, 4),
            "average_cash": round(self.average_cash, 2),
            "total_cash": round(self.total_cash, 2),
            "average_age_years": round(self.average_age_years, 2),
            "household_count": self.household_count,
            "life_stage_counts": self.life_stage_counts,
            "role_counts": self.role_counts,
        }


def calculate_metrics(
    agents: dict[str, Agent], household_count: int = 0
) -> CityMetrics:
    """Calculate aggregate city metrics from current agent population."""
    total = len(agents)
    if total == 0:
        return CityMetrics()

    alive = [a for a in agents.values() if a.alive]
    alive_count = len(alive)

    if alive_count == 0:
        return CityMetrics(total_population=total, alive_population=0)

    total_health = sum(a.health for a in alive)
    total_cash = sum(a.cash for a in alive)
    total_age = sum(a.age_years for a in alive)

    life_stage_counts: dict[str, int] = {}
    role_counts: dict[str, int] = {}

    for a in alive:
        ls_val = a.life_stage.value
        life_stage_counts[ls_val] = life_stage_counts.get(ls_val, 0) + 1

        role_val = a.role.value if hasattr(a.role, "value") else str(a.role)
        role_counts[role_val] = role_counts.get(role_val, 0) + 1

    return CityMetrics(
        total_population=total,
        alive_population=alive_count,
        average_health=total_health / alive_count,
        average_cash=total_cash / alive_count,
        total_cash=total_cash,
        average_age_years=total_age / alive_count,
        household_count=household_count,
        life_stage_counts=life_stage_counts,
        role_counts=role_counts,
    )
