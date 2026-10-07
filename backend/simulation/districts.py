"""HIVEMIND District Entity and Management Module."""

from dataclasses import dataclass

from backend.app.config import get_default_districts


@dataclass
class District:
    id: str
    name: str
    land_price: float
    rent: float
    safety_score: float
    transport_connectivity: float
    housing_units: int
    population: int = 0
    unrest_score: float = 0.0  # Composite unrest index [0.0, 1.0]
    is_rioting: bool = False  # True when unrest breaches critical riot threshold
    riot_days: int = 0  # Consecutive days of active rioting

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "land_price": round(self.land_price, 2),
            "rent": round(self.rent, 2),
            "safety_score": round(self.safety_score, 4),
            "transport_connectivity": round(self.transport_connectivity, 4),
            "housing_units": self.housing_units,
            "population": self.population,
            "unrest_score": round(self.unrest_score, 4),
            "is_rioting": self.is_rioting,
            "riot_days": self.riot_days,
        }


def initialize_districts() -> dict[str, District]:
    """Create the initial 10 districts from standard configuration."""
    districts = {}
    for cfg in get_default_districts():
        districts[cfg.id] = District(
            id=cfg.id,
            name=cfg.name,
            land_price=cfg.base_land_price,
            rent=cfg.base_rent,
            safety_score=cfg.safety_score,
            transport_connectivity=cfg.transport_connectivity,
            housing_units=cfg.housing_units,
            population=0,
        )
    return districts
