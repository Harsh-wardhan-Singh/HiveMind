"""HIVEMIND Corporate Firm Entity Module."""

from dataclasses import dataclass, field
from typing import Any

from backend.companies.production import calculate_cobb_douglas_output
from backend.economy.goods import CommodityType


@dataclass
class Company:
    id: str
    name: str
    district_id: str
    commodity_type: CommodityType
    capital: float = 10_000.0
    cash: float = 25_000.0
    inventory: float = 200.0
    target_wage: float = 120.0  # Daily wage offered
    tfp: float = 1.0  # Total factor productivity
    employee_ids: list[str] = field(default_factory=list)
    daily_revenue: float = 0.0
    daily_expenses: float = 0.0
    daily_profit: float = 0.0
    solvency: bool = True

    def add_employee(self, agent_id: str) -> None:
        if agent_id not in self.employee_ids:
            self.employee_ids.append(agent_id)

    def remove_employee(self, agent_id: str) -> None:
        if agent_id in self.employee_ids:
            self.employee_ids.remove(agent_id)

    def produce(self, worker_skills: list[float]) -> float:
        """Execute daily Cobb-Douglas production and add output to inventory."""
        if not self.solvency:
            return 0.0
        output = calculate_cobb_douglas_output(
            tfp=self.tfp,
            capital=self.capital,
            worker_skills=worker_skills,
        )
        self.inventory += output
        return output

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "district_id": self.district_id,
            "commodity_type": (
                self.commodity_type.value
                if hasattr(self.commodity_type, "value")
                else str(self.commodity_type)
            ),
            "capital": round(self.capital, 2),
            "cash": round(self.cash, 2),
            "inventory": round(self.inventory, 2),
            "target_wage": round(self.target_wage, 2),
            "tfp": round(self.tfp, 4),
            "employee_count": len(self.employee_ids),
            "employee_ids": list(self.employee_ids),
            "daily_revenue": round(self.daily_revenue, 2),
            "daily_expenses": round(self.daily_expenses, 2),
            "daily_profit": round(self.daily_profit, 2),
            "solvency": self.solvency,
        }

