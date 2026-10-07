"""HIVEMIND City Metrics Module (Phase 3 Economic Version)."""

from dataclasses import dataclass, field
from typing import Any

from backend.agents.agent import Agent
from backend.companies.company import Company
from backend.economy.market import MarketState


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

    # Macroeconomic Telemetry (Phase 3)
    cpi: float = 100.0
    inflation_rate: float = 0.0
    unemployment_rate: float = 0.0
    gdp: float = 0.0
    total_corporate_profit: float = 0.0
    average_wage: float = 0.0
    company_count: int = 0

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
            "cpi": round(self.cpi, 2),
            "inflation_rate": round(self.inflation_rate, 2),
            "unemployment_rate": round(self.unemployment_rate, 4),
            "gdp": round(self.gdp, 2),
            "total_corporate_profit": round(self.total_corporate_profit, 2),
            "average_wage": round(self.average_wage, 2),
            "company_count": self.company_count,
        }


def calculate_metrics(
    agents: dict[str, Agent],
    household_count: int = 0,
    companies: dict[str, Company] | None = None,
    market: MarketState | None = None,
    cpi: float = 100.0,
    inflation_rate: float = 0.0,
) -> CityMetrics:
    """Calculate aggregate city metrics from current agents, companies, and market telemetry."""
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
    employed_count = 0

    for a in alive:
        ls_val = a.life_stage.value
        life_stage_counts[ls_val] = life_stage_counts.get(ls_val, 0) + 1

        role_val = a.role.value if hasattr(a.role, "value") else str(a.role)
        role_counts[role_val] = role_counts.get(role_val, 0) + 1

        if a.employer_id is not None:
            employed_count += 1

    # Macroeconomic calculations
    unemployment_rate = (
        (alive_count - employed_count) / alive_count if alive_count > 0 else 0.0
    )

    tot_profit = 0.0
    tot_revenue = 0.0
    tot_wages = 0.0
    comp_count = 0

    if companies:
        comp_count = len(companies)
        for comp in companies.values():
            if comp.solvency:
                tot_profit += comp.daily_profit
                tot_revenue += comp.daily_revenue
                tot_wages += comp.daily_expenses

    avg_wage = tot_wages / employed_count if employed_count > 0 else 0.0
    # Daily GDP = Corporate Revenues + Wages Paid
    daily_gdp = tot_revenue + tot_wages

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
        cpi=cpi,
        inflation_rate=inflation_rate,
        unemployment_rate=unemployment_rate,
        gdp=daily_gdp,
        total_corporate_profit=tot_profit,
        average_wage=avg_wage,
        company_count=comp_count,
    )
