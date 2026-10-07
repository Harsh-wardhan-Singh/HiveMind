"""HIVEMIND Authoritative World State Model."""

from dataclasses import dataclass, field
from typing import Any

from backend.agents.agent import Agent
from backend.banking.bank import MunicipalBank
from backend.companies.company import Company
from backend.economy.inflation import InflationTracker
from backend.economy.market import MarketState, initialize_market_state
from backend.markets.equities import ShareRegistry
from backend.markets.order_book import OrderBook
from backend.politics.government import MunicipalGovernment
from backend.politics.policies import PolicyManager
from backend.simulation.clock import SimulationClock
from backend.simulation.districts import District, initialize_districts
from backend.simulation.metrics import CityMetrics, calculate_metrics
from backend.society.households import Household
from backend.society.relationships import RelationshipGraph


@dataclass
class WorldState:
    run_id: str
    seed: int
    clock: SimulationClock = field(default_factory=SimulationClock)
    districts: dict[str, District] = field(default_factory=initialize_districts)
    agents: dict[str, Agent] = field(default_factory=dict)
    households: dict[str, Household] = field(default_factory=dict)
    relationships: RelationshipGraph = field(default_factory=RelationshipGraph)
    companies: dict[str, Company] = field(default_factory=dict)
    market: MarketState = field(default_factory=initialize_market_state)
    inflation_tracker: InflationTracker = field(default_factory=InflationTracker)
    bank: MunicipalBank = field(default_factory=MunicipalBank)
    share_registry: ShareRegistry = field(default_factory=ShareRegistry)
    order_books: dict[str, OrderBook] = field(default_factory=dict)
    daily_dividends_paid: float = 0.0
    government: MunicipalGovernment = field(default_factory=MunicipalGovernment)
    policy_manager: PolicyManager = field(default_factory=PolicyManager)
    election_interval_days: int = 180
    last_election_tick: int = 0
    snap_election_requested: bool = False
    metrics: CityMetrics = field(default_factory=CityMetrics)
    active_policies: dict[str, Any] = field(default_factory=dict)

    def sync_metrics(self) -> CityMetrics:
        """Update and recalculate population metrics and district population counts."""
        self.active_policies = self.policy_manager.to_dict()
        self.metrics = calculate_metrics(
            agents=self.agents,
            household_count=len(self.households),
            companies=self.companies,
            market=self.market,
            cpi=self.inflation_tracker.current_cpi,
            inflation_rate=self.inflation_tracker.current_inflation_rate,
            order_books=self.order_books,
            bank=self.bank,
            daily_dividends=self.daily_dividends_paid,
            government=self.government,
            districts=self.districts,
            active_policies=self.active_policies,
        )

        # Reset and recalculate district populations
        for d in self.districts.values():
            d.population = 0
        for a in self.agents.values():
            if a.alive and a.district_id in self.districts:
                self.districts[a.district_id].population += 1

        return self.metrics

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "seed": self.seed,
            "tick": self.clock.current_tick,
            "districts": {k: d.to_dict() for k, d in self.districts.items()},
            "agent_count": len(self.agents),
            "household_count": len(self.households),
            "company_count": len(self.companies),
            "market": self.market.to_dict(),
            "bank": self.bank.to_dict(),
            "government": self.government.to_dict(),
            "policies": self.policy_manager.to_dict(),
            "metrics": self.metrics.to_dict(),
            "active_policies": self.active_policies,
        }
