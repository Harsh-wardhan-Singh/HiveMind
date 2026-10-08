"""HIVEMIND Core Simulation Engine (Phase 3 Economic & Market Version)."""

import uuid

from backend.agents.agent import Agent
from backend.agents.lifecycle import evaluate_daily_mortality
from backend.agents.personality import generate_personality
from backend.agents.roles import RoleType
from backend.app.config import SimulationConfig
from backend.companies.company import Company
from backend.economy.consumption import (
    calculate_household_demands,
    settle_household_consumption,
)
from backend.economy.goods import CommodityType
from backend.economy.inflation import InflationTracker
from backend.economy.market import (
    clear_commodity_market,
    initialize_market_state,
)
from backend.events.event_bus import EventBus
from backend.events.event_store import EventStore
from backend.events.event_types import Event, create_event
from backend.information.observation import (
    ObservationPacket,
    generate_agent_observation,
)
from backend.labor.market import match_labor_market, process_daily_payroll
from backend.llm.gateway import StrategicLLMGateway
from backend.llm.provider import OllamaProvider
from backend.markets.order_book import OrderBook
from backend.markets.trading import execute_daily_equity_trading
from backend.persistence.db import create_db_engine_and_factory
from backend.politics import (
    apply_election_result,
    conduct_election,
    evaluate_district_unrest,
    process_active_riots,
    quell_district_riots,
    update_all_favorability,
)
from backend.politics.policies import ActivePolicy, PolicyType
from backend.simulation.clock import SimulationClock
from backend.simulation.districts import initialize_districts
from backend.simulation.rng import SeededRNG
from backend.simulation.state import WorldState
from backend.society.households import create_household
from backend.society.relationships import RelationType


class SimulationEngine:
    """
    Authoritative simulation orchestrator executing discrete daily ticks.
    Guarantees deterministic progression, economic feedback loops, and periodic snapshotting.
    """

    def __init__(self, config: SimulationConfig | None = None):
        self.config: SimulationConfig = config or SimulationConfig()
        self.run_id: str = self.config.run_id or f"run_{uuid.uuid4().hex[:8]}"

        # Initialize persistence with dedicated DB engine and session factory
        self._db_engine, session_factory = create_db_engine_and_factory(
            self.config.database_url
        )
        self.event_store: EventStore = EventStore(session_factory=session_factory)
        self.rng: SeededRNG = SeededRNG(self.config.seed)
        self.event_bus: EventBus = EventBus()

        # Build gateway from configuration (with automatic fallback to mathematics)
        provider = None
        if self.config.llm_enabled:
            provider = OllamaProvider(
                base_url=self.config.llm_base_url,
                model=self.config.llm_model,
            )
        gateway = StrategicLLMGateway(
            provider=provider,
            model=self.config.llm_model,
            base_url=self.config.llm_base_url,
            enabled=self.config.llm_enabled,
        )
        self.llm_gateway = gateway

        # Build initial world state
        self.state: WorldState = WorldState(
            run_id=self.run_id,
            seed=self.config.seed,
            clock=SimulationClock(current_tick=0),
            districts=initialize_districts(),
            agents={},
            households={},
            companies={},
            market=initialize_market_state(),
            inflation_tracker=InflationTracker(),
            llm_gateway=gateway,
        )

        self._initialize_simulation()

    def _initialize_simulation(self) -> None:
        """Populate initial agents, households, companies, and persist day 0 baseline."""
        self.event_store.record_run(
            run_id=self.run_id,
            seed=self.config.seed,
            total_days=self.config.total_days,
            name=self.config.city.name,
        )

        init_events: list[Event] = []

        # 1. Deterministic agent population setup
        agent_rng = self.rng.get_stream("agent_init")
        district_ids = list(self.state.districts.keys())

        roles_pool = [
            RoleType.MANUAL_WORKER,
            RoleType.SKILLED_WORKER,
            RoleType.ENGINEER,
            RoleType.TEACHER,
            RoleType.HEALTHCARE_WORKER,
            RoleType.RESEARCHER,
            RoleType.BUSINESS_OWNER,
            RoleType.INVESTOR,
            RoleType.STUDENT,
            RoleType.UNEMPLOYED,
        ]

        created_agents: list[Agent] = []

        for idx in range(1, self.config.city.starting_population + 1):
            agent_id = f"agent_{idx:04d}"
            sex = "M" if agent_rng.random() < 0.5 else "F"

            # Sample age between 18 and 65 years
            age_years = agent_rng.randint(18, 65)
            age_days = int(age_years * 365.25) + agent_rng.randint(0, 364)

            # Assign role based on age
            if age_years < 23 and agent_rng.random() < 0.6:
                role = RoleType.STUDENT
                edu_level = 1
                skill = round(agent_rng.uniform(0.2, 0.4), 2)
            else:
                role = roles_pool[agent_rng.randint(0, len(roles_pool) - 1)]
                edu_level = agent_rng.randint(1, 3)
                skill = round(agent_rng.uniform(0.4, 0.9), 2)

            # Mayor assignment for the first agent
            if idx == 1:
                role = RoleType.MAYOR
                edu_level = 3
                skill = 0.85
                self.state.government.current_mayor_id = agent_id

            district_id = district_ids[agent_rng.randint(0, len(district_ids) - 1)]
            cash = round(agent_rng.uniform(1500.0, 12000.0), 2)
            health = round(agent_rng.uniform(0.85, 1.0), 4)
            personality = generate_personality(agent_rng)

            agent = Agent(
                id=agent_id,
                age_days=age_days,
                sex=sex,
                role=role,
                personality=personality,
                district_id=district_id,
                cash=cash,
                health=health,
                education_level=edu_level,
                skills=skill,
                alive=True,
            )
            self.state.agents[agent_id] = agent
            created_agents.append(agent)

            evt = create_event(
                run_id=self.run_id,
                tick=0,
                event_type="AgentCreated",
                payload=agent.to_dict(),
            )
            init_events.append(evt)
            self.event_bus.publish(evt)

        # 2. Form initial households
        hh_rng = self.rng.get_stream("household_init")
        unassigned_agents = list(created_agents)

        while unassigned_agents:
            head = unassigned_agents.pop(0)
            hh = create_household(
                district_id=head.district_id,
                head_agent_id=head.id,
                initial_cash=head.cash,
            )
            head.household_id = hh.id

            if unassigned_agents and hh_rng.random() < 0.4:
                partner = unassigned_agents.pop(0)
                partner.district_id = head.district_id
                partner.household_id = hh.id
                hh.add_member(partner.id)
                hh.pooled_cash += partner.cash

                self.state.relationships.add_edge(
                    head.id, partner.id, RelationType.SPOUSE, trust=0.9
                )
                self.state.relationships.add_edge(
                    partner.id, head.id, RelationType.SPOUSE, trust=0.9
                )

            self.state.households[hh.id] = hh

            hh_evt = create_event(
                run_id=self.run_id,
                tick=0,
                event_type="HouseholdFormed",
                payload=hh.to_dict(),
            )
            init_events.append(hh_evt)
            self.event_bus.publish(hh_evt)

        # 3. Form initial Companies across districts & issue equities
        comp_configs = [
            (
                "comp_food_01",
                "AGRI",
                "Central Agriculture & Mills",
                "dist_north",
                CommodityType.FOOD,
                15000.0,
                30000.0,
                110.0,
            ),
            (
                "comp_food_02",
                "FOOD",
                "Hivemind Fresh Foods",
                "dist_suburban",
                CommodityType.FOOD,
                12000.0,
                25000.0,
                105.0,
            ),
            (
                "comp_food_03",
                "FARM",
                "South Valley Farms",
                "dist_south",
                CommodityType.FOOD,
                14000.0,
                28000.0,
                100.0,
            ),
            (
                "comp_house_01",
                "HOUS",
                "City Housing Works",
                "dist_central",
                CommodityType.HOUSING,
                25000.0,
                45000.0,
                130.0,
            ),
            (
                "comp_house_02",
                "BLDR",
                "Suburban Builders Co.",
                "dist_suburban",
                CommodityType.HOUSING,
                20000.0,
                35000.0,
                125.0,
            ),
            (
                "comp_health_01",
                "HLTH",
                "Metropolitan Health Services",
                "dist_central",
                CommodityType.HEALTHCARE,
                30000.0,
                50000.0,
                150.0,
            ),
            (
                "comp_health_02",
                "CLNC",
                "Community Medical Clinic",
                "dist_east",
                CommodityType.HEALTHCARE,
                18000.0,
                30000.0,
                140.0,
            ),
            (
                "comp_goods_01",
                "METL",
                "Industrial Forge & Tools",
                "dist_industrial",
                CommodityType.CONSUMER_GOODS,
                22000.0,
                40000.0,
                120.0,
            ),
            (
                "comp_goods_02",
                "APPL",
                "Hivemind Appliance Co.",
                "dist_industrial",
                CommodityType.CONSUMER_GOODS,
                19000.0,
                35000.0,
                115.0,
            ),
        ]

        # Identify prospective initial shareholders (investors and business owners)
        investors = [
            a
            for a in created_agents
            if a.role in (RoleType.INVESTOR, RoleType.BUSINESS_OWNER)
        ]

        for (
            c_id,
            c_ticker,
            c_name,
            c_dist,
            c_comm,
            c_cap,
            c_cash,
            c_wage,
        ) in comp_configs:
            comp = Company(
                id=c_id,
                name=c_name,
                district_id=c_dist,
                commodity_type=c_comm,
                capital=c_cap,
                cash=c_cash,
                target_wage=c_wage,
                inventory=50.0,
                ticker=c_ticker,
                shares_outstanding=10_000,
            )
            self.state.companies[c_id] = comp

            # Shareholder allocation: allocate shares to investors, remainder in treasury
            initial_holders: dict[str, int] = {}
            allocated = 0
            for inv in investors:
                inv_shares = 500
                initial_holders[inv.id] = inv_shares
                inv.portfolio[c_ticker] = inv.portfolio.get(c_ticker, 0) + inv_shares
                allocated += inv_shares

            initial_holders[c_id] = max(0, 10_000 - allocated)
            self.state.share_registry.issue_shares(
                company_id=c_id,
                ticker=c_ticker,
                total_shares=10_000,
                initial_holders=initial_holders,
            )

            # Initialize double auction order book
            self.state.order_books[c_ticker] = OrderBook(
                ticker=c_ticker, initial_price=10.0
            )

            c_evt = create_event(
                run_id=self.run_id,
                tick=0,
                event_type="CompanyFounded",
                payload=comp.to_dict(),
            )
            init_events.append(c_evt)
            self.event_bus.publish(c_evt)

        # 4. Initial Bank Account Funding
        for a in created_agents:
            if a.cash > 2500.0:
                dep_amt = round(a.cash * 0.25, 2)
                a.cash -= dep_amt
                self.state.bank.deposit(a.id, dep_amt)
                a.bank_deposit = dep_amt

        for comp in self.state.companies.values():
            c_dep = round(comp.cash * 0.20, 2)
            comp.cash -= c_dep
            self.state.bank.deposit(comp.id, c_dep)

        # 5. Initial labor market match
        labor_rng = self.rng.get_stream("labor_init")
        match_labor_market(self.state.agents, self.state.companies, labor_rng)

        # 6. Sync metrics & emit initialization event
        self.state.sync_metrics()

        govt_evt = create_event(
            run_id=self.run_id,
            tick=0,
            event_type="GovernmentInitialized",
            payload=self.state.government.to_dict(),
        )
        init_events.append(govt_evt)
        self.event_bus.publish(govt_evt)

        init_evt = create_event(
            run_id=self.run_id,
            tick=0,
            event_type="SimulationInitialized",
            payload={
                "run_id": self.run_id,
                "seed": self.config.seed,
                "population": len(self.state.agents),
                "households": len(self.state.households),
                "companies": len(self.state.companies),
                "districts": len(self.state.districts),
                "metrics": self.state.metrics.to_dict(),
            },
        )
        init_events.append(init_evt)
        self.event_bus.publish(init_evt)

        # Batch write events and save initial snapshot
        self.event_store.append_events(init_events)
        self._save_snapshot()

    def step(self) -> list[Event]:
        """
        Execute one discrete daily tick (1 tick = 1 day).
        Follows the canonical pipeline: Clock -> Aging -> Labor & Payroll ->
        Cobb-Douglas Production -> Market Clearing -> CPI & Inflation ->
        Household Consumption -> Financial Settlement -> Metrics.
        """
        # 1. Advance discrete calendar clock
        tick = self.state.clock.advance(1)
        day_events: list[Event] = []

        # 2. Demographic aging & actuarial mortality
        demo_rng = self.rng.get_stream("demographics")
        for agent in list(self.state.agents.values()):
            if not agent.alive:
                continue

            agent.age_days += 1
            health_delta = demo_rng.uniform(-0.0005, 0.0003)
            agent.health = max(0.0, min(1.0, agent.health + health_delta))

            if agent.health <= 0.0 or evaluate_daily_mortality(
                agent.age_years, agent.health, demo_rng
            ):
                agent.alive = False

                # Remove from household
                if agent.household_id and agent.household_id in self.state.households:
                    hh = self.state.households[agent.household_id]
                    hh.remove_member(agent.id)
                    if hh.size == 0:
                        del self.state.households[hh.id]

                # Remove from employer
                if agent.employer_id and agent.employer_id in self.state.companies:
                    self.state.companies[agent.employer_id].remove_employee(agent.id)

                # Purge social graph edges
                self.state.relationships.remove_agent(agent.id)

                evt = create_event(
                    run_id=self.run_id,
                    tick=tick,
                    event_type="AgentDied",
                    payload={
                        "agent_id": agent.id,
                        "age_years": agent.age_years,
                        "role": (
                            agent.role.value
                            if hasattr(agent.role, "value")
                            else str(agent.role)
                        ),
                        "cause": (
                            "natural_mortality"
                            if agent.health > 0.0
                            else "health_exhaustion"
                        ),
                    },
                )
                day_events.append(evt)
                self.event_bus.publish(evt)

        # 3. Labor Market Matching & Daily Payroll Disbursement
        labor_rng = self.rng.get_stream("labor")
        new_hires = match_labor_market(
            self.state.agents, self.state.companies, labor_rng
        )
        for emp_id, comp_id in new_hires:
            day_events.append(
                create_event(
                    run_id=self.run_id,
                    tick=tick,
                    event_type="AgentEmployed",
                    payload={"agent_id": emp_id, "company_id": comp_id},
                )
            )

        process_daily_payroll(self.state.agents, self.state.companies)

        # 4. Corporate Production Phase (Cobb-Douglas Y = A * K^alpha * L^beta)
        for comp in self.state.companies.values():
            if not comp.solvency:
                continue
            skills = [
                self.state.agents[emp_id].skills
                for emp_id in comp.employee_ids
                if emp_id in self.state.agents and self.state.agents[emp_id].alive
            ]
            comp.produce(skills)

        # 4b. Strategic Corporate Strategy (Phase 7 - LLM Gateway with Mathematical Fallback)
        for comp in self.state.companies.values():
            if comp.solvency and (comp.cash < 500.0 or comp.inventory > 100.0):
                ceo = next(
                    (
                        self.state.agents[emp_id]
                        for emp_id in comp.employee_ids
                        if emp_id in self.state.agents
                        and self.state.agents[emp_id].role == RoleType.BUSINESS_OWNER
                    ),
                    None,
                )
                if not ceo and comp.employee_ids:
                    first_emp = comp.employee_ids[0]
                    if first_emp in self.state.agents:
                        ceo = self.state.agents[first_emp]
                if ceo:
                    corp_decision = self.state.llm_gateway.decide_corporate_strategy(
                        ceo, comp, self.state
                    )
                    strat_corp_evt = create_event(
                        run_id=self.run_id,
                        tick=tick,
                        event_type="StrategicDecisionMade",
                        payload=corp_decision.to_dict(),
                    )
                    day_events.append(strat_corp_evt)
                    self.event_bus.publish(strat_corp_evt)
                    break

        # 5. Goods Supply/Demand & Walrasian Market Clearing
        demands = calculate_household_demands(self.state.agents, self.state.households)
        fill_ratios = clear_commodity_market(
            market=self.state.market,
            companies=self.state.companies,
            household_demands=demands,
        )

        # 6. Update Laspeyres CPI & Inflation Index
        self.state.inflation_tracker.update(self.state.market.prices)

        # 7. Household Consumption Settlement & Nutritional Feedback
        food_sub = self.state.policy_manager.get_food_subsidy_fraction()
        settle_household_consumption(
            agents=self.state.agents,
            households=self.state.households,
            market_prices=self.state.market.prices,
            fill_ratios=fill_ratios,
            food_subsidy_rate=food_sub,
        )

        # 8. Financial Markets & Banking Operations (Phase 4)
        # 8a. Service Bank Interest & Loans
        self.state.bank.service_daily_banking(
            agents=self.state.agents,
            companies=self.state.companies,
            current_tick=tick,
        )

        # 8b. Corporate Dividend Declarations & Payouts
        total_dividends = 0.0
        for comp in self.state.companies.values():
            div_paid = self.state.share_registry.declare_and_distribute_dividends(
                company=comp,
                agents=self.state.agents,
                payout_ratio=0.35,
            )
            total_dividends += div_paid
        self.state.daily_dividends_paid = total_dividends

        # 8c. Continuous Double Auction Stock Trading
        equity_rng = self.rng.get_stream("equity_trading")
        for ob in self.state.order_books.values():
            ob.reset_daily_stats()

        trades = execute_daily_equity_trading(
            order_books=self.state.order_books,
            registry=self.state.share_registry,
            agents=self.state.agents,
            companies=self.state.companies,
            rng=equity_rng,
            current_tick=tick,
        )
        for tr in trades:
            day_events.append(
                create_event(
                    run_id=self.run_id,
                    tick=tick,
                    event_type="EquityTraded",
                    payload=tr.to_dict(),
                )
            )

        # 9. Municipal Governance, Politics & Policies (Phase 5)
        # 9a. Tax Assessment & Collection
        taxes = self.state.government.collect_daily_taxes(
            agents=self.state.agents,
            companies=self.state.companies,
            households=self.state.households,
            districts=self.state.districts,
        )
        if taxes["total_tax_revenue"] > 0:
            day_events.append(
                create_event(
                    run_id=self.run_id,
                    tick=tick,
                    event_type="TaxCollected",
                    payload=taxes,
                )
            )

        # 9b. Public Services, Civil Payroll & Infrastructure Maintenance
        self.state.government.disburse_public_services(
            agents=self.state.agents,
            districts=self.state.districts,
        )

        # 9c. Corruption Leak & Scandal Exposure
        pol_rng = self.rng.get_stream("politics")
        sitting_mayor = self.state.agents.get(self.state.government.current_mayor_id)
        _leak, scandal = self.state.government.process_corruption_leak(
            rng=pol_rng,
            sitting_mayor=sitting_mayor,
            current_tick=tick,
        )
        if scandal:
            scandal_evt = create_event(
                run_id=self.run_id,
                tick=tick,
                event_type="CorruptionScandalExposed",
                payload={
                    "tick": tick,
                    "corruption_index": round(
                        self.state.government.corruption_index, 4
                    ),
                    "total_embezzled": round(self.state.government.total_embezzled, 2),
                    "sitting_mayor_id": self.state.government.current_mayor_id,
                },
            )
            day_events.append(scandal_evt)
            self.event_bus.publish(scandal_evt)

        # 9d. Policy Lifecycle & Autonomous Governance Interventions
        expired_pols = self.state.policy_manager.step_policies(
            current_tick=tick,
            government=self.state.government,
            households=self.state.households,
            agents=self.state.agents,
            districts=self.state.districts,
        )
        for exp_id in expired_pols:
            day_events.append(
                create_event(
                    run_id=self.run_id,
                    tick=tick,
                    event_type="PolicyExpired",
                    payload={"policy_id": exp_id},
                )
            )

        new_pols = self.state.policy_manager.evaluate_auto_governance(
            government=self.state.government,
            avg_favorability=self.state.metrics.city_favorability,
            avg_unrest=self.state.metrics.city_unrest,
            rioting_count=self.state.metrics.rioting_districts_count,
            cpi=self.state.inflation_tracker.current_cpi,
            current_tick=tick,
            rng=pol_rng,
        )
        for np in new_pols:
            np_evt = create_event(
                run_id=self.run_id,
                tick=tick,
                event_type="PolicyEnacted",
                payload=np.to_dict(),
            )
            day_events.append(np_evt)
            self.event_bus.publish(np_evt)

        # 9d-1. Strategic Mayoral Deliberation (Phase 7 - Local LLM Gateway with 100% Math Fallback)
        mayor = self.state.agents.get(self.state.government.current_mayor_id)
        if (
            mayor
            and mayor.alive
            and (
                self.state.metrics.rioting_districts_count > 0
                or self.state.metrics.city_unrest > 0.25
                or self.state.metrics.inflation_rate > 7.0
                or self.state.government.corruption_index > 0.08
                or tick % 30 == 0
            )
        ):
            mayor_decision = self.state.llm_gateway.decide_mayoral_crisis(
                mayor, self.state
            )
            strat_evt = create_event(
                run_id=self.run_id,
                tick=tick,
                event_type="StrategicDecisionMade",
                payload=mayor_decision.to_dict(),
            )
            day_events.append(strat_evt)
            self.event_bus.publish(strat_evt)

            if mayor_decision.chosen_action != "NO_ACTION":
                pol_enum = getattr(PolicyType, mayor_decision.chosen_action, None)
                if pol_enum:
                    pol_id = f"pol_{mayor_decision.chosen_action.lower()}"
                    if pol_id not in self.state.policy_manager.active_policies:
                        mag = (
                            35.0
                            if pol_enum == PolicyType.WELFARE_STIMULUS
                            else (20.0 if pol_enum == PolicyType.PUBLIC_WORKS else 0.25)
                        )
                        enacted_pol = ActivePolicy(
                            policy_id=pol_id,
                            policy_type=pol_enum,
                            description=f"Strategic Decree: {mayor_decision.rationale[:60]}",
                            magnitude=mag,
                            start_tick=tick,
                            duration_days=30,
                        )
                        self.state.policy_manager.enact_policy(enacted_pol)
                        np_evt = create_event(
                            run_id=self.run_id,
                            tick=tick,
                            event_type="PolicyEnacted",
                            payload=enacted_pol.to_dict(),
                        )
                        day_events.append(np_evt)
                        self.event_bus.publish(np_evt)

        # 9e. Favorability & Citizen Approval Rating Update
        avg_fav, _approval_pct = update_all_favorability(
            agents=self.state.agents,
            districts=self.state.districts,
            inflation_rate=self.state.inflation_tracker.current_inflation_rate,
            corruption_index=self.state.government.corruption_index,
            has_recent_scandal=scandal,
        )
        if avg_fav < 0.35:
            self.state.government.consecutive_low_favorability_days += 1
        else:
            self.state.government.consecutive_low_favorability_days = 0

        # 9f. Civil Unrest & Riots Evaluation
        unrest_scores, new_riots = evaluate_district_unrest(
            districts=self.state.districts,
            agents=self.state.agents,
            corruption_index=self.state.government.corruption_index,
        )
        for r_dist_id in new_riots:
            r_evt = create_event(
                run_id=self.run_id,
                tick=tick,
                event_type="RiotStarted",
                payload={
                    "district_id": r_dist_id,
                    "unrest_score": unrest_scores.get(r_dist_id, 0.0),
                },
            )
            day_events.append(r_evt)
            self.event_bus.publish(r_evt)

        process_active_riots(
            districts=self.state.districts,
            companies=self.state.companies,
            agents=self.state.agents,
            government=self.state.government,
            rng=pol_rng,
        )

        quelled = quell_district_riots(self.state.districts)
        for q_dist_id in quelled:
            q_evt = create_event(
                run_id=self.run_id,
                tick=tick,
                event_type="RiotQuelled",
                payload={"district_id": q_dist_id},
            )
            day_events.append(q_evt)
            self.event_bus.publish(q_evt)

        # 9g. Democratic Elections & Mayoral Succession
        scheduled_election = (
            tick - self.state.last_election_tick
        ) >= self.state.election_interval_days
        snap_election = (
            self.state.government.consecutive_low_favorability_days >= 30
            or len(new_riots) >= 2
            or self.state.snap_election_requested
        )

        if scheduled_election or snap_election:
            election_res = conduct_election(
                agents=self.state.agents,
                districts=self.state.districts,
                government=self.state.government,
                current_tick=tick,
                rng=pol_rng,
            )
            transferred, message = apply_election_result(
                result=election_res,
                government=self.state.government,
                agents=self.state.agents,
            )
            self.state.last_election_tick = tick
            self.state.snap_election_requested = False

            elec_evt = create_event(
                run_id=self.run_id,
                tick=tick,
                event_type="ElectionHeld",
                payload=election_res.to_dict(),
            )
            day_events.append(elec_evt)
            self.event_bus.publish(elec_evt)

            if transferred:
                trans_evt = create_event(
                    run_id=self.run_id,
                    tick=tick,
                    event_type="MayoralTransition",
                    payload={
                        "tick": tick,
                        "new_mayor_id": election_res.winner_id,
                        "new_mayor_name": election_res.winner_name,
                        "platform": election_res.winner_platform,
                        "message": message,
                    },
                )
                day_events.append(trans_evt)
                self.event_bus.publish(trans_evt)

        # 10. Information Ecology, Media, Rumors & Society Harmony (Phase 6)
        # 10a. News Publication
        info_rng = self.rng.get_stream("information")
        news_articles = self.state.media_engine.generate_daily_news(
            world_state=self.state,
            rng=info_rng,
        )
        for art in news_articles:
            art_evt = create_event(
                run_id=self.run_id,
                tick=tick,
                event_type="NewsPublished",
                payload=art.to_dict(),
            )
            day_events.append(art_evt)
            self.event_bus.publish(art_evt)

        # 10b. Organic Contextual Rumor Spawning
        rumor_rng = self.rng.get_stream("rumors")
        new_rumors = self.state.rumor_engine.trigger_contextual_rumors(
            world_state=self.state,
            rng=rumor_rng,
        )
        for rm in new_rumors:
            rm_evt = create_event(
                run_id=self.run_id,
                tick=tick,
                event_type="RumorSpawned",
                payload=rm.to_dict(),
            )
            day_events.append(rm_evt)
            self.event_bus.publish(rm_evt)

        # 10c. Word-of-Mouth Diffusion along Social Graph Edges
        transmissions = self.state.rumor_engine.diffuse_rumors(
            agents=self.state.agents,
            relationships=self.state.relationships,
            current_tick=tick,
            rng=rumor_rng,
        )
        if transmissions:
            diff_evt = create_event(
                run_id=self.run_id,
                tick=tick,
                event_type="RumorDiffused",
                payload={
                    "tick": tick,
                    "transmissions_count": len(transmissions),
                    "active_rumors_count": len(self.state.rumor_engine.active_rumors),
                },
            )
            day_events.append(diff_evt)
            self.event_bus.publish(diff_evt)

        # 10d. Society Harmony Index & Feedback
        harmony_idx, distrust, unrest_pen = self.state.harmony_tracker.update_harmony(
            world_state=self.state,
            active_rumors=self.state.rumor_engine.active_rumors,
            relationships=self.state.relationships,
        )
        # Apply disharmony feedback to citizen unrest and favorability
        if unrest_pen > 0:
            for agent in self.state.agents.values():
                if agent.alive:
                    agent.unrest = min(1.0, round(agent.unrest + unrest_pen * 0.15, 4))
                    agent.favorability = max(
                        0.0, round(agent.favorability - unrest_pen * 0.20, 4)
                    )

        harm_evt = create_event(
            run_id=self.run_id,
            tick=tick,
            event_type="HarmonyShifted",
            payload={
                "tick": tick,
                "harmony_index": harmony_idx,
                "interpersonal_distrust": distrust,
                "unrest_penalty": unrest_pen,
            },
        )
        day_events.append(harm_evt)
        self.event_bus.publish(harm_evt)

        # 11. Recalculate and Synchronize Macro, Political & Social Telemetry
        self.state.sync_metrics()

        # 12. Emit day completion event
        day_evt = create_event(
            run_id=self.run_id,
            tick=tick,
            event_type="DayTicked",
            payload={
                "tick": tick,
                "date": self.state.clock.format_date(),
                "metrics": self.state.metrics.to_dict(),
                "market": self.state.market.to_dict(),
            },
        )
        day_events.append(day_evt)
        self.event_bus.publish(day_evt)

        # 13. Persist events
        self.event_store.append_events(day_events)

        # 14. Periodic snapshotting
        if tick % self.config.snapshot_interval_days == 0:
            self._save_snapshot()

        return day_events

    def run(self, days: int | None = None) -> WorldState:
        """Advance the simulation continuously for the specified number of days."""
        target_days = days if days is not None else self.config.total_days
        for _ in range(target_days):
            self.step()
        return self.state

    def get_agent_observation(self, agent_id: str) -> ObservationPacket | None:
        """Retrieve a bounded, noisy observation packet tailored to an individual agent's horizon."""
        agent = self.state.agents.get(agent_id)
        if not agent:
            return None
        obs_rng = self.rng.get_stream(f"obs_{agent_id}_{self.state.clock.current_tick}")
        headlines = [a.to_dict() for a in self.state.media_engine.daily_articles]
        beliefs = self.state.rumor_engine.agent_beliefs.get(agent_id, {})
        rumors = [{"topic": t, "belief": b} for t, b in beliefs.items()]
        return generate_agent_observation(
            agent=agent,
            world_state=self.state,
            rng=obs_rng,
            headlines=headlines,
            rumors=rumors,
        )

    def _save_snapshot(self) -> None:
        """Persist current WorldState as a point-in-time snapshot."""
        snapshot_id = f"snap_{self.run_id}_{self.state.clock.current_tick:05d}"
        self.event_store.save_snapshot(
            snapshot_id=snapshot_id,
            run_id=self.run_id,
            tick=self.state.clock.current_tick,
            state_blob=self.state.to_dict(),
        )

    def close(self) -> None:
        """Dispose of the database engine and release open connections."""
        if hasattr(self, "_db_engine") and self._db_engine is not None:
            self._db_engine.dispose()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
