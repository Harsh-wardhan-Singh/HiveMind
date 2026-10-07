"""HIVEMIND Political Candidates & Campaign Platforms Module."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PoliticalPlatform:
    """Policy platform proposed by a political candidate."""

    name: str
    income_tax_mid: float = 0.10
    corporate_tax: float = 0.15
    welfare_generosity: float = 0.50  # [0.0, 1.0]
    anti_corruption_pledge: float = 0.50  # [0.0, 1.0]
    infrastructure_investment: float = 0.50  # [0.0, 1.0]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "income_tax_mid": round(self.income_tax_mid, 4),
            "corporate_tax": round(self.corporate_tax, 4),
            "welfare_generosity": round(self.welfare_generosity, 2),
            "anti_corruption_pledge": round(self.anti_corruption_pledge, 2),
            "infrastructure_investment": round(self.infrastructure_investment, 2),
        }


@dataclass
class Candidate:
    """Electoral candidate contesting the Mayoral race."""

    candidate_id: str
    agent_id: str
    name: str
    role: str
    platform: PoliticalPlatform = field(
        default_factory=lambda: PoliticalPlatform("Standard Civic Platform")
    )
    charisma: float = 0.50  # Public appeal factor [0.0, 1.0]
    integrity: float = 0.50  # Perceived honesty and anti-corruption stance [0.0, 1.0]
    is_incumbent: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role,
            "platform": self.platform.to_dict(),
            "charisma": round(self.charisma, 4),
            "integrity": round(self.integrity, 4),
            "is_incumbent": self.is_incumbent,
        }
