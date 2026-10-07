"""HIVEMIND Core Agent Data Model (Phase 2 Demographic & Societal Model)."""

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from backend.agents.lifecycle import LifeStage, get_life_stage
from backend.agents.personality import Personality
from backend.agents.roles import RoleType


def _default_personality() -> Personality:
    return Personality(
        openness=0.5,
        conscientiousness=0.5,
        extraversion=0.5,
        agreeableness=0.5,
        neuroticism=0.5,
        risk_tolerance=0.5,
        social_trust=0.5,
        ambition=0.5,
    )


@dataclass
class Agent:
    id: str
    age_days: int
    district_id: str
    cash: float
    sex: str = "M"  # "M" or "F"
    role: RoleType = RoleType.UNEMPLOYED
    personality: Personality = field(default_factory=_default_personality)
    debt: float = 0.0
    assets: float = 0.0
    health: float = 1.0
    education_level: int = 1  # 0: None, 1: HighSchool, 2: Bachelor, 3: Master/PhD
    skills: float = 0.5  # Effective skill multiplier [0.1, 1.0]
    household_id: str | None = None
    employer_id: str | None = None
    alive: bool = True
    immigrant: bool = False
    birth_generation: int = 0
    portfolio: dict[str, int] = field(default_factory=dict)
    bank_deposit: float = 0.0
    bank_loan: float = 0.0
    favorability: float = 0.5  # Rating of municipal government [0.0, 1.0]
    unrest: float = 0.0  # Propensity towards civil unrest / protest [0.0, 1.0]
    public_help_received: float = 0.0  # Recent welfare / subsidy assistance
    last_tax_paid: float = 0.0  # Most recent daily taxes paid

    @property
    def age_years(self) -> int:
        return math.floor(self.age_days / 365.25)

    @property
    def life_stage(self) -> LifeStage:
        return get_life_stage(self.age_years)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "age_days": self.age_days,
            "age_years": self.age_years,
            "sex": self.sex,
            "role": self.role.value if isinstance(self.role, Enum) else str(self.role),
            "life_stage": self.life_stage.value,
            "district_id": self.district_id,
            "household_id": self.household_id,
            "employer_id": self.employer_id,
            "cash": round(self.cash, 2),
            "debt": round(self.debt, 2),
            "assets": round(self.assets, 2),
            "bank_deposit": round(self.bank_deposit, 2),
            "bank_loan": round(self.bank_loan, 2),
            "favorability": round(self.favorability, 4),
            "unrest": round(self.unrest, 4),
            "public_help_received": round(self.public_help_received, 2),
            "last_tax_paid": round(self.last_tax_paid, 2),
            "portfolio": dict(self.portfolio),
            "health": round(self.health, 4),
            "education_level": self.education_level,
            "skills": round(self.skills, 4),
            "alive": self.alive,
            "immigrant": self.immigrant,
            "birth_generation": self.birth_generation,
            "personality": self.personality.to_dict(),
        }
