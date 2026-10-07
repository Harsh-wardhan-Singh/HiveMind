"""HIVEMIND City Metrics Module."""

from dataclasses import dataclass

from backend.simulation.agent import Agent


@dataclass
class CityMetrics:
    total_population: int = 0
    alive_population: int = 0
    average_health: float = 0.0
    average_cash: float = 0.0
    total_cash: float = 0.0
    average_age_years: float = 0.0

    def to_dict(self) -> dict:
        return {
            "total_population": self.total_population,
            "alive_population": self.alive_population,
            "average_health": round(self.average_health, 4),
            "average_cash": round(self.average_cash, 2),
            "total_cash": round(self.total_cash, 2),
            "average_age_years": round(self.average_age_years, 2),
        }


def calculate_metrics(agents: dict[str, Agent]) -> CityMetrics:
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

    return CityMetrics(
        total_population=total,
        alive_population=alive_count,
        average_health=total_health / alive_count,
        average_cash=total_cash / alive_count,
        total_cash=total_cash,
        average_age_years=total_age / alive_count,
    )
