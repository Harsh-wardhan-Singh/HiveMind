"""HIVEMIND Municipal Government, Public Budget & Taxation Module."""

import random
from dataclasses import dataclass, field
from typing import Any

from backend.agents.agent import Agent
from backend.agents.roles import RoleType, get_role_definition
from backend.companies.company import Company
from backend.simulation.districts import District
from backend.society.households import Household


@dataclass
class TaxRates:
    """Progressive taxation schedule and corporate/property tax rates."""

    income_tax_low: float = 0.0  # 0% on subsistence daily income (<= 50 C)
    income_tax_mid: float = 0.10  # 10% on middle income (50 - 180 C)
    income_tax_high: float = 0.22  # 22% on high income (> 180 C)
    corporate_tax: float = 0.15  # 15% on positive daily net profits
    property_tax: float = 0.0005  # Daily levy on district land valuation (~1.8% annual)

    def to_dict(self) -> dict[str, float]:
        return {
            "income_tax_low": round(self.income_tax_low, 4),
            "income_tax_mid": round(self.income_tax_mid, 4),
            "income_tax_high": round(self.income_tax_high, 4),
            "corporate_tax": round(self.corporate_tax, 4),
            "property_tax": round(self.property_tax, 6),
        }


@dataclass
class MunicipalGovernment:
    """
    Authoritative Municipal Government managing public budget, taxation,
    public service payroll, corruption leaks, and emergency relief.
    """

    treasury: float = 100_000.0  # Municipal liquidity in Credits
    tax_rates: TaxRates = field(default_factory=TaxRates)
    corruption_index: float = 0.05  # Graft factor [0.0, 1.0]
    total_embezzled: float = 0.0  # Cumulative siphoned funds
    current_mayor_id: str = ""
    daily_tax_revenue: float = 0.0
    daily_income_tax: float = 0.0
    daily_corporate_tax: float = 0.0
    daily_property_tax: float = 0.0
    daily_expenditures: float = 0.0
    daily_public_payroll: float = 0.0
    daily_infrastructure_cost: float = 0.0
    daily_welfare_paid: float = 0.0
    daily_corruption_leak: float = 0.0
    consecutive_low_favorability_days: int = 0
    total_elections_held: int = 0
    last_scandal_tick: int = -1

    def calculate_income_tax(self, daily_wage: float) -> float:
        """Calculate progressive income tax liability for a daily wage amount."""
        if daily_wage <= 50.0:
            return 0.0
        elif daily_wage <= 180.0:
            return (daily_wage - 50.0) * self.tax_rates.income_tax_mid
        else:
            mid_tax = (180.0 - 50.0) * self.tax_rates.income_tax_mid
            high_tax = (daily_wage - 180.0) * self.tax_rates.income_tax_high
            return mid_tax + high_tax

    def collect_daily_taxes(
        self,
        agents: dict[str, Agent],
        companies: dict[str, Company],
        households: dict[str, Household],
        districts: dict[str, District],
    ) -> dict[str, float]:
        """
        Assess and collect income, corporate, and property taxes across the city.
        Returns a breakdown of collected taxes.
        """
        total_income_tax = 0.0
        total_corp_tax = 0.0
        total_prop_tax = 0.0

        # 1. Income tax from employed agents
        for agent in agents.values():
            if not agent.alive:
                agent.last_tax_paid = 0.0
                continue

            tax_liability = 0.0
            if agent.employer_id and agent.employer_id in companies:
                comp = companies[agent.employer_id]
                tax_liability = self.calculate_income_tax(comp.target_wage)
            elif agent.role in (
                RoleType.TEACHER,
                RoleType.HEALTHCARE_WORKER,
                RoleType.RESEARCHER,
                RoleType.MAYOR,
            ):
                base_wage = get_role_definition(agent.role).base_daily_wage
                tax_liability = self.calculate_income_tax(base_wage)

            # Deduct from agent cash if solvent
            actual_tax = min(agent.cash, tax_liability)
            if actual_tax > 0.0:
                agent.cash -= actual_tax
                total_income_tax += actual_tax
            agent.last_tax_paid = actual_tax

        # 2. Corporate profit tax on positive net profits
        for comp in companies.values():
            if not comp.solvency or comp.daily_profit <= 0.0:
                continue

            corp_liability = comp.daily_profit * self.tax_rates.corporate_tax
            actual_corp_tax = min(comp.cash, corp_liability)
            if actual_corp_tax > 0.0:
                comp.cash -= actual_corp_tax
                total_corp_tax += actual_corp_tax

        # 3. Property tax on district residence
        for hh in households.values():
            if hh.district_id in districts:
                dist = districts[hh.district_id]
                prop_val = dist.land_price * 10.0
                prop_tax = prop_val * self.tax_rates.property_tax
                actual_prop_tax = min(hh.pooled_cash, prop_tax)
                if actual_prop_tax > 0.0:
                    hh.pooled_cash -= actual_prop_tax
                    total_prop_tax += actual_prop_tax

        # Credit municipal treasury
        total_collected = total_income_tax + total_corp_tax + total_prop_tax
        self.treasury += total_collected
        self.daily_income_tax = total_income_tax
        self.daily_corporate_tax = total_corp_tax
        self.daily_property_tax = total_prop_tax
        self.daily_tax_revenue = total_collected

        return {
            "income_tax": total_income_tax,
            "corporate_tax": total_corp_tax,
            "property_tax": total_prop_tax,
            "total_tax_revenue": total_collected,
        }

    def disburse_public_services(
        self,
        agents: dict[str, Agent],
        districts: dict[str, District],
        public_works_multiplier: float = 1.0,
    ) -> float:
        """
        Disburse civil servant payroll (Mayor, unattached teachers/doctors/researchers)
        and district infrastructure maintenance costs from the municipal treasury.
        """
        payroll = 0.0
        infra_cost = 0.0

        reserve_floor = min(5_000.0, self.treasury * 0.20)
        spendable_total = max(0.0, self.treasury - reserve_floor)

        # Fiscal discipline: if treasury falls below 15,000 C, cap disbursements to daily tax intake
        budget_limit = (
            spendable_total
            if self.treasury > 15_000.0
            else max(self.daily_tax_revenue, 600.0)
        )
        spendable_pool = min(spendable_total, budget_limit)

        # Public servant payroll
        for agent in agents.values():
            if not agent.alive:
                continue

            # Civil servants not employed by private companies are on the municipal payroll
            if agent.employer_id is None and agent.role in (
                RoleType.TEACHER,
                RoleType.HEALTHCARE_WORKER,
                RoleType.RESEARCHER,
                RoleType.MAYOR,
            ):
                daily_wage = get_role_definition(agent.role).base_daily_wage
                payout = min(daily_wage, spendable_pool)
                if payout > 0.0:
                    self.treasury -= payout
                    spendable_pool -= payout
                    agent.cash += payout
                    payroll += payout
                if spendable_pool <= 0.0:
                    break

        # District infrastructure maintenance
        for dist in districts.values():
            maint_budget = 20.0 * public_works_multiplier
            if (self.treasury - maint_budget) >= reserve_floor:
                self.treasury -= maint_budget
                infra_cost += maint_budget
                dist.safety_score = min(1.0, dist.safety_score + 0.001)
            elif self.treasury > 0.0:
                part = min(self.treasury, maint_budget * 0.5)
                self.treasury -= part
                infra_cost += part
                dist.safety_score = min(1.0, dist.safety_score + 0.0005)
            else:
                # Underfunded infrastructure degrades safety
                dist.safety_score = max(0.1, dist.safety_score - 0.005)

        total_exp = payroll + infra_cost
        self.daily_public_payroll = payroll
        self.daily_infrastructure_cost = infra_cost
        self.daily_expenditures = total_exp
        return total_exp

    def process_corruption_leak(
        self,
        rng: random.Random,
        sitting_mayor: Agent | None,
        current_tick: int,
    ) -> tuple[float, bool]:
        """
        Simulate corruption leakage and graft.
        A sitting mayor with low conscientiousness and high ambition increases graft.
        May trigger a public corruption scandal if corruption index exceeds 0.15.
        """
        if self.treasury <= 0.0 or self.corruption_index <= 0.0:
            self.daily_corruption_leak = 0.0
            return 0.0, False

        # Modulate graft multiplier based on Mayor's personality
        graft_mod = 1.0
        if sitting_mayor and sitting_mayor.alive:
            p = sitting_mayor.personality
            graft_mod = (1.5 - p.conscientiousness) * (0.8 + 0.4 * p.ambition)

        # Daily graft rate
        leak = self.treasury * (self.corruption_index * 0.0003 * graft_mod)
        leak = min(self.treasury, max(0.0, leak))

        self.treasury -= leak
        self.total_embezzled += leak
        self.daily_corruption_leak = leak

        # Check for public scandal exposure if corruption is high
        scandal_exposed = False
        if (
            self.corruption_index >= 0.15
            and (current_tick - self.last_scandal_tick > 30)
            and rng.random() < (self.corruption_index * 0.25)
        ):
            scandal_exposed = True
            self.last_scandal_tick = current_tick

        return leak, scandal_exposed

    def disburse_welfare(
        self,
        households: dict[str, Household],
        agents: dict[str, Agent],
        poverty_threshold: float = 300.0,
        grant_amount: float = 25.0,
    ) -> float:
        """Disburse emergency welfare assistance to impoverished households."""
        total_welfare = 0.0
        for hh in households.values():
            if hh.pooled_cash < poverty_threshold:
                if self.treasury >= grant_amount:
                    self.treasury -= grant_amount
                    hh.pooled_cash += grant_amount
                    total_welfare += grant_amount
                    # Record help received for all members
                    for m_id in hh.member_agent_ids:
                        if m_id in agents and agents[m_id].alive:
                            agents[m_id].public_help_received += grant_amount
                else:
                    break

        self.daily_welfare_paid = total_welfare
        self.daily_expenditures += total_welfare
        return total_welfare

    def to_dict(self) -> dict[str, Any]:
        return {
            "treasury": round(self.treasury, 2),
            "corruption_index": round(self.corruption_index, 4),
            "total_embezzled": round(self.total_embezzled, 2),
            "current_mayor_id": self.current_mayor_id,
            "daily_tax_revenue": round(self.daily_tax_revenue, 2),
            "daily_income_tax": round(self.daily_income_tax, 2),
            "daily_corporate_tax": round(self.daily_corporate_tax, 2),
            "daily_property_tax": round(self.daily_property_tax, 2),
            "daily_expenditures": round(self.daily_expenditures, 2),
            "daily_public_payroll": round(self.daily_public_payroll, 2),
            "daily_infrastructure_cost": round(self.daily_infrastructure_cost, 2),
            "daily_welfare_paid": round(self.daily_welfare_paid, 2),
            "daily_corruption_leak": round(self.daily_corruption_leak, 2),
            "consecutive_low_favorability_days": self.consecutive_low_favorability_days,
            "total_elections_held": self.total_elections_held,
            "tax_rates": self.tax_rates.to_dict(),
        }
