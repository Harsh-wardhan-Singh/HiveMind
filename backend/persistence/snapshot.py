"""HIVEMIND Authoritative State Snapshot Engine (Phase 8).

Provides full point-in-time serialization and deserialization of WorldState,
guaranteeing complete reconstruction of agents, institutions, markets, and social graphs.
"""

from typing import Any

from backend.agents.agent import Agent
from backend.agents.personality import Personality
from backend.agents.roles import RoleType
from backend.banking.bank import MunicipalBank
from backend.companies.company import Company
from backend.economy.goods import CommodityType
from backend.economy.inflation import InflationTracker
from backend.economy.market import MarketState
from backend.events.event_store import EventStore
from backend.information.harmony import SocietyHarmonyTracker
from backend.information.media import MediaEngine, NewsArticle
from backend.information.rumors import Rumor, RumorEngine
from backend.llm.gateway import StrategicLLMGateway
from backend.markets.equities import EquityShare, ShareRegistry
from backend.markets.order_book import Order, OrderBook, OrderSide, OrderType
from backend.politics.government import MunicipalGovernment, TaxRates
from backend.politics.policies import ActivePolicy, PolicyManager, PolicyType
from backend.simulation.clock import SimulationClock
from backend.simulation.districts import District
from backend.simulation.state import WorldState
from backend.society.households import Household
from backend.society.relationships import RelationshipGraph, RelationType


def serialize_world_state(state: WorldState) -> dict[str, Any]:
    """
    Perform a complete, deep serialization of WorldState into a JSON-compatible dictionary.
    """
    # 1. Districts
    districts_blob = {d_id: d.to_dict() for d_id, d in state.districts.items()}

    # 2. Agents
    agents_blob = {a_id: a.to_dict() for a_id, a in state.agents.items()}

    # 3. Households
    households_blob = {h_id: h.to_dict() for h_id, h in state.households.items()}

    # 4. Companies
    companies_blob = {c_id: c.to_dict() for c_id, c in state.companies.items()}

    # 5. Relationships
    edges_blob = [
        {
            "source": edge.source_agent_id,
            "target": edge.target_agent_id,
            "relation": edge.relation.value,
            "trust": edge.trust,
            "interactions": edge.interaction_count,
        }
        for edge in state.relationships._edges.values()
    ]

    # 6. Market
    market_blob = {
        "prices": {k.value: v for k, v in state.market.prices.items()},
        "inventories": {k.value: v for k, v in state.market.inventories.items()},
        "demands": {k.value: v for k, v in state.market.demands.items()},
        "sales": {k.value: v for k, v in state.market.sales.items()},
    }

    # 7. Inflation Tracker
    inflation_blob = {
        "base_prices": {
            k.value: v for k, v in state.inflation_tracker.base_prices.items()
        },
        "basket_weights": {
            k.value: v for k, v in state.inflation_tracker.basket_weights.items()
        },
        "cpi_history": list(state.inflation_tracker.cpi_history),
        "current_cpi": state.inflation_tracker.current_cpi,
        "current_inflation_rate": state.inflation_tracker.current_inflation_rate,
    }

    # 8. Municipal Bank
    bank_blob = {
        "id": state.bank.id,
        "name": state.bank.name,
        "cash_reserves": state.bank.cash_reserves,
        "reserve_ratio": state.bank.reserve_ratio,
        "deposit_annual_rate": state.bank.deposit_annual_rate,
        "loan_annual_rate": state.bank.loan_annual_rate,
        "deposits": dict(state.bank.deposits),
        "loans": dict(state.bank.loans),
        "daily_interest_paid": state.bank.daily_interest_paid,
        "daily_interest_collected": state.bank.daily_interest_collected,
        "accumulated_bad_debt_writeoffs": state.bank.accumulated_bad_debt_writeoffs,
    }

    # 9. Share Registry
    equities_blob = {}
    for ticker, eq in state.share_registry.equities.items():
        equities_blob[ticker] = {
            "ticker": eq.ticker,
            "company_id": eq.company_id,
            "total_shares": eq.total_shares,
            "par_value": eq.par_value,
            "shareholders": dict(eq.shareholders),
            "dividend_per_share": eq.dividend_per_share,
            "total_dividends_paid": eq.total_dividends_paid,
        }

    # 10. Order Books
    order_books_blob = {}
    for ticker, ob in state.order_books.items():
        order_books_blob[ticker] = {
            "ticker": ob.ticker,
            "last_price": ob.last_price,
            "daily_volume": ob.daily_volume,
            "bids": [order.to_dict() for order in ob.bids],
            "asks": [order.to_dict() for order in ob.asks],
        }

    # 11. Municipal Government
    gov = state.government
    gov_blob = {
        "treasury": gov.treasury,
        "corruption_index": gov.corruption_index,
        "total_embezzled": gov.total_embezzled,
        "current_mayor_id": gov.current_mayor_id,
        "daily_tax_revenue": gov.daily_tax_revenue,
        "daily_income_tax": gov.daily_income_tax,
        "daily_corporate_tax": gov.daily_corporate_tax,
        "daily_property_tax": gov.daily_property_tax,
        "daily_expenditures": gov.daily_expenditures,
        "daily_public_payroll": gov.daily_public_payroll,
        "daily_infrastructure_cost": gov.daily_infrastructure_cost,
        "daily_welfare_paid": gov.daily_welfare_paid,
        "daily_corruption_leak": gov.daily_corruption_leak,
        "consecutive_low_favorability_days": gov.consecutive_low_favorability_days,
        "total_elections_held": gov.total_elections_held,
        "last_scandal_tick": gov.last_scandal_tick,
        "tax_rates": gov.tax_rates.to_dict(),
    }

    # 12. Policy Manager
    policies_blob = {
        p_id: pol.to_dict()
        for p_id, pol in state.policy_manager.active_policies.items()
    }

    # 13. Media Engine
    media_blob = {
        "outlets": {k: v.to_dict() for k, v in state.media_engine.outlets.items()},
        "daily_articles": [a.to_dict() for a in state.media_engine.daily_articles],
        "articles_archive": [a.to_dict() for a in state.media_engine.articles_archive],
    }

    # 14. Rumor Engine
    rumors_blob = {
        "active_rumors": {
            k: v.to_dict() for k, v in state.rumor_engine.active_rumors.items()
        },
        "agent_beliefs": {
            k: dict(v) for k, v in state.rumor_engine.agent_beliefs.items()
        },
    }

    # 15. Society Harmony
    harmony_blob = {
        "harmony_index": state.harmony_tracker.harmony_index,
        "interpersonal_distrust": state.harmony_tracker.interpersonal_distrust,
        "disinformation_index": state.harmony_tracker.disinformation_index,
    }

    # 16. LLM Gateway Telemetry
    llm_blob = {
        "enabled": state.llm_gateway.enabled,
        "total_decisions": state.llm_gateway.total_decisions,
        "llm_decisions": state.llm_gateway.llm_decisions,
        "fallback_decisions": state.llm_gateway.fallback_decisions,
        "total_latency_ms": state.llm_gateway.total_latency_ms,
    }

    return {
        "version": 1,
        "run_id": state.run_id,
        "seed": state.seed,
        "tick": state.clock.current_tick,
        "date": state.clock.format_date(),
        "districts": districts_blob,
        "agents": agents_blob,
        "agent_count": len(state.agents),
        "households": households_blob,
        "companies": companies_blob,
        "relationships": edges_blob,
        "market": market_blob,
        "inflation": inflation_blob,
        "bank": bank_blob,
        "share_registry": equities_blob,
        "order_books": order_books_blob,
        "daily_dividends_paid": state.daily_dividends_paid,
        "government": gov_blob,
        "policies": policies_blob,
        "election_interval_days": state.election_interval_days,
        "last_election_tick": state.last_election_tick,
        "snap_election_requested": state.snap_election_requested,
        "media": media_blob,
        "rumors": rumors_blob,
        "harmony": harmony_blob,
        "llm": llm_blob,
        "metrics": state.metrics.to_dict(),
    }


def deserialize_world_state(
    blob: dict[str, Any], new_run_id: str | None = None
) -> WorldState:
    """
    Reconstruct a fully-functional, authoritative WorldState from a serialized dictionary.
    """
    run_id = new_run_id or blob["run_id"]
    seed = blob.get("seed", 424242)
    tick = blob.get("tick", 0)

    # 1. Simulation Clock
    clock = SimulationClock(current_tick=tick)

    # 2. Districts
    districts: dict[str, District] = {}
    for d_id, d_data in blob.get("districts", {}).items():
        districts[d_id] = District(
            id=d_data["id"],
            name=d_data["name"],
            land_price=float(d_data["land_price"]),
            rent=float(d_data["rent"]),
            safety_score=float(d_data["safety_score"]),
            transport_connectivity=float(d_data["transport_connectivity"]),
            housing_units=int(d_data["housing_units"]),
            population=int(d_data.get("population", 0)),
            unrest_score=float(d_data.get("unrest_score", 0.0)),
            is_rioting=bool(d_data.get("is_rioting", False)),
            riot_days=int(d_data.get("riot_days", 0)),
        )

    # 3. Agents
    agents: dict[str, Agent] = {}
    for a_id, a_data in blob.get("agents", {}).items():
        p_data = a_data.get("personality", {})
        personality = Personality(
            openness=float(p_data.get("openness", 0.5)),
            conscientiousness=float(p_data.get("conscientiousness", 0.5)),
            extraversion=float(p_data.get("extraversion", 0.5)),
            agreeableness=float(p_data.get("agreeableness", 0.5)),
            neuroticism=float(p_data.get("neuroticism", 0.5)),
            risk_tolerance=float(p_data.get("risk_tolerance", 0.5)),
            social_trust=float(p_data.get("social_trust", 0.5)),
            ambition=float(p_data.get("ambition", 0.5)),
        )
        role_val = a_data.get("role", "UNEMPLOYED")
        role_enum = getattr(RoleType, role_val, RoleType.UNEMPLOYED)

        agent = Agent(
            id=a_data["id"],
            age_days=int(a_data["age_days"]),
            district_id=a_data["district_id"],
            cash=float(a_data["cash"]),
            sex=a_data.get("sex", "M"),
            role=role_enum,
            personality=personality,
            debt=float(a_data.get("debt", 0.0)),
            assets=float(a_data.get("assets", 0.0)),
            health=float(a_data.get("health", 1.0)),
            education_level=int(a_data.get("education_level", 1)),
            skills=float(a_data.get("skills", 0.5)),
            household_id=a_data.get("household_id"),
            employer_id=a_data.get("employer_id"),
            alive=bool(a_data.get("alive", True)),
            immigrant=bool(a_data.get("immigrant", False)),
            birth_generation=int(a_data.get("birth_generation", 0)),
            portfolio=dict(a_data.get("portfolio", {})),
            bank_deposit=float(a_data.get("bank_deposit", 0.0)),
            bank_loan=float(a_data.get("bank_loan", 0.0)),
            favorability=float(a_data.get("favorability", 0.5)),
            unrest=float(a_data.get("unrest", 0.0)),
            public_help_received=float(a_data.get("public_help_received", 0.0)),
            last_tax_paid=float(a_data.get("last_tax_paid", 0.0)),
        )
        agents[a_id] = agent

    # 4. Households
    households: dict[str, Household] = {}
    for h_id, h_data in blob.get("households", {}).items():
        households[h_id] = Household(
            id=h_data["id"],
            district_id=h_data["district_id"],
            head_agent_id=h_data["head_agent_id"],
            member_agent_ids=list(h_data.get("member_agent_ids", [])),
            pooled_cash=float(h_data.get("pooled_cash", 0.0)),
            rent_share=float(h_data.get("rent_share", 0.0)),
        )

    # 5. Relationships
    relationships = RelationshipGraph()
    for edge_data in blob.get("relationships", []):
        rel_str = edge_data.get("relation", "FRIEND")
        rel_enum = getattr(RelationType, rel_str, RelationType.FRIEND)
        edge = relationships.add_edge(
            source_id=edge_data["source"],
            target_id=edge_data["target"],
            relation=rel_enum,
            trust=float(edge_data.get("trust", 0.5)),
        )
        edge.interaction_count = int(edge_data.get("interactions", 0))

    # 6. Companies
    companies: dict[str, Company] = {}
    for c_id, c_data in blob.get("companies", {}).items():
        comm_val = c_data.get("commodity_type", "FOOD")
        comm_enum = getattr(CommodityType, comm_val, CommodityType.FOOD)
        companies[c_id] = Company(
            id=c_data["id"],
            name=c_data["name"],
            district_id=c_data["district_id"],
            commodity_type=comm_enum,
            capital=float(c_data.get("capital", 10000.0)),
            cash=float(c_data.get("cash", 25000.0)),
            inventory=float(c_data.get("inventory", 200.0)),
            target_wage=float(c_data.get("target_wage", 120.0)),
            tfp=float(c_data.get("tfp", 1.0)),
            employee_ids=list(c_data.get("employee_ids", [])),
            daily_revenue=float(c_data.get("daily_revenue", 0.0)),
            daily_expenses=float(c_data.get("daily_expenses", 0.0)),
            daily_profit=float(c_data.get("daily_profit", 0.0)),
            solvency=bool(c_data.get("solvency", True)),
            ticker=c_data.get("ticker", ""),
            shares_outstanding=int(c_data.get("shares_outstanding", 10000)),
            bank_loan=float(c_data.get("bank_loan", 0.0)),
            dividend_yield=float(c_data.get("dividend_yield", 0.0)),
        )

    # 7. Market State
    m_data = blob.get("market", {})
    market = MarketState(
        prices={
            getattr(CommodityType, k, CommodityType.FOOD): float(v)
            for k, v in m_data.get("prices", {}).items()
        },
        inventories={
            getattr(CommodityType, k, CommodityType.FOOD): float(v)
            for k, v in m_data.get("inventories", {}).items()
        },
        demands={
            getattr(CommodityType, k, CommodityType.FOOD): float(v)
            for k, v in m_data.get("demands", {}).items()
        },
        sales={
            getattr(CommodityType, k, CommodityType.FOOD): float(v)
            for k, v in m_data.get("sales", {}).items()
        },
    )

    # 8. Inflation Tracker
    inf_data = blob.get("inflation", {})
    inflation_tracker = InflationTracker(
        base_prices={
            getattr(CommodityType, k, CommodityType.FOOD): float(v)
            for k, v in inf_data.get("base_prices", {}).items()
        },
        basket_weights={
            getattr(CommodityType, k, CommodityType.FOOD): float(v)
            for k, v in inf_data.get("basket_weights", {}).items()
        },
        cpi_history=list(inf_data.get("cpi_history", [])),
        current_cpi=float(inf_data.get("current_cpi", 100.0)),
        current_inflation_rate=float(inf_data.get("current_inflation_rate", 0.0)),
    )

    # 9. Municipal Bank
    b_data = blob.get("bank", {})
    bank = MunicipalBank(
        id=b_data.get("id", "bank_municipal_01"),
        name=b_data.get("name", "Hivemind Municipal Commercial Bank"),
        cash_reserves=float(b_data.get("cash_reserves", 150000.0)),
        reserve_ratio=float(b_data.get("reserve_ratio", 0.10)),
        deposit_annual_rate=float(b_data.get("deposit_annual_rate", 0.03)),
        loan_annual_rate=float(b_data.get("loan_annual_rate", 0.07)),
        deposits={k: float(v) for k, v in b_data.get("deposits", {}).items()},
        loans={k: float(v) for k, v in b_data.get("loans", {}).items()},
        daily_interest_paid=float(b_data.get("daily_interest_paid", 0.0)),
        daily_interest_collected=float(b_data.get("daily_interest_collected", 0.0)),
        accumulated_bad_debt_writeoffs=float(
            b_data.get("accumulated_bad_debt_writeoffs", 0.0)
        ),
    )

    # 10. Share Registry
    share_registry = ShareRegistry()
    for ticker, eq_data in blob.get("share_registry", {}).items():
        eq = EquityShare(
            ticker=ticker,
            company_id=eq_data["company_id"],
            total_shares=int(eq_data.get("total_shares", 10000)),
            par_value=float(eq_data.get("par_value", 10.0)),
            shareholders={
                k: int(v) for k, v in eq_data.get("shareholders", {}).items()
            },
            dividend_per_share=float(eq_data.get("dividend_per_share", 0.0)),
            total_dividends_paid=float(eq_data.get("total_dividends_paid", 0.0)),
        )
        share_registry.equities[ticker] = eq

    # 11. Order Books
    order_books: dict[str, OrderBook] = {}
    for ticker, ob_data in blob.get("order_books", {}).items():
        ob = OrderBook(ticker=ticker)
        ob.last_price = float(ob_data.get("last_price", 10.0))
        ob.daily_volume = int(ob_data.get("daily_volume", 0))
        for b in ob_data.get("bids", []):
            order = Order(
                id=b["id"],
                trader_id=b["trader_id"],
                ticker=ticker,
                side=OrderSide.BUY,
                order_type=getattr(
                    OrderType, b.get("order_type", "LIMIT"), OrderType.LIMIT
                ),
                price=float(b["price"]),
                quantity=int(b["quantity"]),
                filled_quantity=int(b.get("filled_quantity", 0)),
                created_tick=int(b.get("created_tick", 0)),
            )
            ob.bids.append(order)
        for a in ob_data.get("asks", []):
            order = Order(
                id=a["id"],
                trader_id=a["trader_id"],
                ticker=ticker,
                side=OrderSide.SELL,
                order_type=getattr(
                    OrderType, a.get("order_type", "LIMIT"), OrderType.LIMIT
                ),
                price=float(a["price"]),
                quantity=int(a["quantity"]),
                filled_quantity=int(a.get("filled_quantity", 0)),
                created_tick=int(a.get("created_tick", 0)),
            )
            ob.asks.append(order)
        order_books[ticker] = ob

    # 12. Municipal Government
    gov_data = blob.get("government", {})
    tr_data = gov_data.get("tax_rates", {})
    tax_rates = TaxRates(
        income_tax_low=float(tr_data.get("income_tax_low", 0.0)),
        income_tax_mid=float(tr_data.get("income_tax_mid", 0.10)),
        income_tax_high=float(tr_data.get("income_tax_high", 0.22)),
        corporate_tax=float(tr_data.get("corporate_tax", 0.15)),
        property_tax=float(tr_data.get("property_tax", 0.0005)),
    )
    government = MunicipalGovernment(
        treasury=float(gov_data.get("treasury", 100000.0)),
        tax_rates=tax_rates,
        corruption_index=float(gov_data.get("corruption_index", 0.05)),
        total_embezzled=float(gov_data.get("total_embezzled", 0.0)),
        current_mayor_id=gov_data.get("current_mayor_id", ""),
        daily_tax_revenue=float(gov_data.get("daily_tax_revenue", 0.0)),
        daily_income_tax=float(gov_data.get("daily_income_tax", 0.0)),
        daily_corporate_tax=float(gov_data.get("daily_corporate_tax", 0.0)),
        daily_property_tax=float(gov_data.get("daily_property_tax", 0.0)),
        daily_expenditures=float(gov_data.get("daily_expenditures", 0.0)),
        daily_public_payroll=float(gov_data.get("daily_public_payroll", 0.0)),
        daily_infrastructure_cost=float(gov_data.get("daily_infrastructure_cost", 0.0)),
        daily_welfare_paid=float(gov_data.get("daily_welfare_paid", 0.0)),
        daily_corruption_leak=float(gov_data.get("daily_corruption_leak", 0.0)),
        consecutive_low_favorability_days=int(
            gov_data.get("consecutive_low_favorability_days", 0)
        ),
        total_elections_held=int(gov_data.get("total_elections_held", 0)),
        last_scandal_tick=int(gov_data.get("last_scandal_tick", -1)),
    )

    # 13. Policy Manager
    policy_manager = PolicyManager()
    for p_id, p_data in blob.get("policies", {}).items():
        pol_type_val = p_data.get("policy_type", "FOOD_SUBSIDY")
        pol_type_enum = getattr(PolicyType, pol_type_val, PolicyType.FOOD_SUBSIDY)
        policy_manager.active_policies[p_id] = ActivePolicy(
            policy_id=p_data["policy_id"],
            policy_type=pol_type_enum,
            description=p_data.get("description", ""),
            magnitude=float(p_data.get("magnitude", 0.0)),
            start_tick=int(p_data.get("start_tick", 0)),
            duration_days=int(p_data.get("duration_days", 30)),
            daily_cost=float(p_data.get("daily_cost", 0.0)),
        )

    # 14. Media Engine
    media_engine = MediaEngine()
    m_eng_data = blob.get("media", {})
    daily_arts = []
    for art in m_eng_data.get("daily_articles", []):
        daily_arts.append(
            NewsArticle(
                article_id=art["article_id"],
                headline=art["headline"],
                topic=art.get("topic", "GENERAL"),
                summary=art.get("summary", ""),
                sentiment=float(art.get("sentiment", 0.0)),
                credibility=float(art.get("credibility", 1.0)),
                publisher=art.get("publisher", "Press"),
                tick=int(art.get("tick", tick)),
            )
        )
    media_engine.daily_articles = daily_arts
    archive_arts = []
    for art in m_eng_data.get("articles_archive", []):
        archive_arts.append(
            NewsArticle(
                article_id=art["article_id"],
                headline=art["headline"],
                topic=art.get("topic", "GENERAL"),
                summary=art.get("summary", ""),
                sentiment=float(art.get("sentiment", 0.0)),
                credibility=float(art.get("credibility", 1.0)),
                publisher=art.get("publisher", "Press"),
                tick=int(art.get("tick", tick)),
            )
        )
    media_engine.articles_archive = archive_arts

    # 15. Rumor Engine
    rumor_engine = RumorEngine()
    r_eng_data = blob.get("rumors", {})
    for r_id, r_data in r_eng_data.get("active_rumors", {}).items():
        rumor_engine.active_rumors[r_id] = Rumor(
            rumor_id=r_data["rumor_id"],
            topic=r_data["topic"],
            headline=r_data["headline"],
            intensity=float(r_data.get("intensity", 0.5)),
            veracity=float(r_data.get("veracity", 0.5)),
            origin_tick=int(r_data.get("origin_tick", tick)),
            transmission_count=int(
                r_data.get("transmissions", r_data.get("transmission_count", 0))
            ),
        )
    for ag_id, beliefs in r_eng_data.get("agent_beliefs", {}).items():
        rumor_engine.agent_beliefs[ag_id] = {k: float(v) for k, v in beliefs.items()}

    # 16. Harmony Tracker
    h_data = blob.get("harmony", {})
    harmony_tracker = SocietyHarmonyTracker(
        harmony_index=float(h_data.get("harmony_index", 0.85)),
        interpersonal_distrust=float(h_data.get("interpersonal_distrust", 0.15)),
        disinformation_index=float(h_data.get("disinformation_index", 0.0)),
    )

    # 17. Strategic LLM Gateway
    llm_data = blob.get("llm", {})
    gateway = StrategicLLMGateway(enabled=bool(llm_data.get("enabled", False)))
    gateway.total_decisions = int(llm_data.get("total_decisions", 0))
    gateway.llm_decisions = int(llm_data.get("llm_decisions", 0))
    gateway.fallback_decisions = int(llm_data.get("fallback_decisions", 0))
    gateway.total_latency_ms = float(llm_data.get("total_latency_ms", 0.0))

    # Assemble WorldState
    world_state = WorldState(
        run_id=run_id,
        seed=seed,
        clock=clock,
        districts=districts,
        agents=agents,
        households=households,
        relationships=relationships,
        companies=companies,
        market=market,
        inflation_tracker=inflation_tracker,
        bank=bank,
        share_registry=share_registry,
        order_books=order_books,
        daily_dividends_paid=float(blob.get("daily_dividends_paid", 0.0)),
        government=government,
        policy_manager=policy_manager,
        election_interval_days=int(blob.get("election_interval_days", 180)),
        last_election_tick=int(blob.get("last_election_tick", 0)),
        snap_election_requested=bool(blob.get("snap_election_requested", False)),
        media_engine=media_engine,
        rumor_engine=rumor_engine,
        harmony_tracker=harmony_tracker,
        llm_gateway=gateway,
    )

    world_state.sync_metrics()
    return world_state


def clone_world_state(state: WorldState, new_run_id: str | None = None) -> WorldState:
    """
    Produce an identical, in-memory decoupled clone of WorldState.
    """
    serialized = serialize_world_state(state)
    return deserialize_world_state(serialized, new_run_id=new_run_id)


class SnapshotManager:
    """
    Coordinates saving and loading point-in-time full WorldState snapshots
    against the underlying event store.
    """

    def __init__(self, event_store: EventStore):
        self.event_store = event_store

    def save_snapshot(self, world_state: WorldState) -> str:
        """Serialize and persist current WorldState."""
        tick = world_state.clock.current_tick
        snapshot_id = f"snap_{world_state.run_id}_{tick:05d}"
        blob = serialize_world_state(world_state)
        self.event_store.save_snapshot(
            snapshot_id=snapshot_id,
            run_id=world_state.run_id,
            tick=tick,
            state_blob=blob,
        )
        return snapshot_id

    def load_snapshot(self, run_id: str, tick: int) -> WorldState | None:
        """Load and deserialize WorldState from an exact snapshot tick."""
        snap = self.event_store.get_snapshot_at_tick(run_id=run_id, tick=tick)
        if not snap or "state_blob" not in snap:
            return None
        return deserialize_world_state(snap["state_blob"])

    def load_latest_snapshot(
        self, run_id: str, up_to_tick: int | None = None
    ) -> WorldState | None:
        """Load and deserialize the most recent snapshot available up to tick."""
        snap = self.event_store.get_latest_snapshot(
            run_id=run_id, up_to_tick=up_to_tick
        )
        if not snap or "state_blob" not in snap:
            return None
        return deserialize_world_state(snap["state_blob"])
