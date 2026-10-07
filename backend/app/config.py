"""HIVEMIND Application Configuration Module."""

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DistrictConfig(BaseModel):
    id: str
    name: str
    base_land_price: float = 1000.0
    base_rent: float = 500.0
    safety_score: float = 0.8
    transport_connectivity: float = 0.7
    housing_units: int = 40


class CityConfig(BaseModel):
    name: str = "Hivemind City"
    area_km2: float = 100.0
    starting_population: int = 100
    base_currency: str = "C"
    starting_gdp: float = 10_000_000.0
    initial_tax_rate: float = 0.10
    initial_interest_rate: float = 0.05
    initial_food_supply: float = 100_000.0
    initial_housing_units: int = 350
    initial_public_budget: float = 1_000_000.0


class SimulationConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="HIVEMIND_", env_file=".env", extra="ignore"
    )

    run_id: str | None = None
    seed: int = 424242
    total_days: int = 365
    snapshot_interval_days: int = 30
    database_url: str = "sqlite:///hivemind.db"
    llm_enabled: bool = False

    city: CityConfig = Field(default_factory=CityConfig)


def get_default_districts() -> list[DistrictConfig]:
    """Return the canonical 10 districts for Hivemind City."""
    return [
        DistrictConfig(
            id="dist_central",
            name="Central",
            base_land_price=2500.0,
            base_rent=1200.0,
            safety_score=0.85,
            transport_connectivity=0.95,
            housing_units=60,
        ),
        DistrictConfig(
            id="dist_north",
            name="North",
            base_land_price=1200.0,
            base_rent=600.0,
            safety_score=0.80,
            transport_connectivity=0.75,
            housing_units=40,
        ),
        DistrictConfig(
            id="dist_south",
            name="South",
            base_land_price=1100.0,
            base_rent=550.0,
            safety_score=0.75,
            transport_connectivity=0.70,
            housing_units=40,
        ),
        DistrictConfig(
            id="dist_east",
            name="East",
            base_land_price=1050.0,
            base_rent=520.0,
            safety_score=0.78,
            transport_connectivity=0.72,
            housing_units=35,
        ),
        DistrictConfig(
            id="dist_west",
            name="West",
            base_land_price=1150.0,
            base_rent=580.0,
            safety_score=0.82,
            transport_connectivity=0.78,
            housing_units=35,
        ),
        DistrictConfig(
            id="dist_industrial",
            name="Industrial",
            base_land_price=600.0,
            base_rent=350.0,
            safety_score=0.60,
            transport_connectivity=0.85,
            housing_units=25,
        ),
        DistrictConfig(
            id="dist_university",
            name="University",
            base_land_price=1400.0,
            base_rent=650.0,
            safety_score=0.88,
            transport_connectivity=0.88,
            housing_units=45,
        ),
        DistrictConfig(
            id="dist_suburban",
            name="Suburban",
            base_land_price=900.0,
            base_rent=480.0,
            safety_score=0.92,
            transport_connectivity=0.60,
            housing_units=50,
        ),
        DistrictConfig(
            id="dist_low_income",
            name="Low-income",
            base_land_price=450.0,
            base_rent=250.0,
            safety_score=0.50,
            transport_connectivity=0.55,
            housing_units=40,
        ),
        DistrictConfig(
            id="dist_high_income",
            name="High-income",
            base_land_price=3500.0,
            base_rent=1800.0,
            safety_score=0.96,
            transport_connectivity=0.90,
            housing_units=30,
        ),
    ]
