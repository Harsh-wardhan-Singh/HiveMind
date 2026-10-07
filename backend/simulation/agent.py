"""HIVEMIND Core Agent Data Model (Phase 1 Kernel Version)."""

import math
from dataclasses import dataclass


@dataclass
class Agent:
    id: str
    age_days: int
    district_id: str
    cash: float
    health: float = 1.0
    alive: bool = True

    @property
    def age_years(self) -> int:
        return math.floor(self.age_days / 365.25)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "age_days": self.age_days,
            "age_years": self.age_years,
            "district_id": self.district_id,
            "cash": round(self.cash, 2),
            "health": round(self.health, 4),
            "alive": self.alive,
        }

