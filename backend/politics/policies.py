"""HIVEMIND Government Policies, Emergency Interventions & Reform Engine Module."""

import random
from dataclasses import dataclass
from enum import Enum
from typing import Any

from backend.agents.agent import Agent
from backend.politics.government import MunicipalGovernment
from backend.simulation.districts import District
from backend.society.households import Household


class PolicyType(str, Enum):
    FOOD_SUBSIDY = "FOOD_SUBSIDY"
    WELFARE_STIMULUS = "WELFARE_STIMULUS"
    PUBLIC_WORKS = "PUBLIC_WORKS"
    ANTI_CORRUPTION_CRACKDOWN = "ANTI_CORRUPTION_CRACKDOWN"
    AUSTERITY = "AUSTERITY"
    TAX_CUT = "TAX_CUT"


@dataclass
class ActivePolicy:
    """An active government policy or executive emergency decree."""

    policy_id: str
    policy_type: PolicyType
    description: str
    magnitude: float
    start_tick: int
    duration_days: int
    daily_cost: float = 0.0

    def is_expired(self, current_tick: int) -> bool:
        return current_tick >= (self.start_tick + self.duration_days)

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "policy_type": self.policy_type.value,
            "description": self.description,
            "magnitude": round(self.magnitude, 4),
            "start_tick": self.start_tick,
            "duration_days": self.duration_days,
            "daily_cost": round(self.daily_cost, 2),
        }


class PolicyManager:
    """Oversees policy lifecycle, emergency triggers, and societal execution."""

    def __init__(self) -> None:
        self.active_policies: dict[str, ActivePolicy] = {}

    def enact_policy(self, policy: ActivePolicy) -> None:
        """Enact or replace an active policy."""
        self.active_policies[policy.policy_id] = policy

    def revoke_policy(self, policy_id: str) -> ActivePolicy | None:
        """Prematurely repeal a policy."""
        return self.active_policies.pop(policy_id, None)

    def get_food_subsidy_fraction(self) -> float:
        """Aggregate active food subsidy co-pay fraction from municipal treasury [0.0, 0.50]."""
        sub = 0.0
        for pol in self.active_policies.values():
            if pol.policy_type == PolicyType.FOOD_SUBSIDY:
                sub += pol.magnitude
        return min(0.50, sub)

    def step_policies(
        self,
        current_tick: int,
        government: MunicipalGovernment,
        households: dict[str, Household],
        agents: dict[str, Agent],
        districts: dict[str, District],
    ) -> list[str]:
        """
        Execute daily policy effects and decommission expired decrees.
        Returns list of expired policy IDs.
        """
        expired_ids: list[str] = []

        for pol_id, pol in list(self.active_policies.items()):
            if pol.is_expired(current_tick):
                expired_ids.append(pol_id)
                del self.active_policies[pol_id]
                continue

            # Execute daily operational effect
            if pol.policy_type == PolicyType.WELFARE_STIMULUS:
                # Disburse stimulus checks to low-income households
                if government.treasury >= 500.0:
                    disbursed = government.disburse_welfare(
                        households=households,
                        agents=agents,
                        poverty_threshold=400.0,
                        grant_amount=pol.magnitude,
                    )
                    pol.daily_cost = disbursed

            elif pol.policy_type == PolicyType.PUBLIC_WORKS:
                # Employ unemployed citizens in civic infrastructure repairs
                work_wage = pol.magnitude
                civic_cost = 0.0
                unemployed_agents = [
                    a for a in agents.values() if a.alive and a.employer_id is None
                ]
                for u_agent in unemployed_agents[:5]:  # Up to 5 temporary civic hires
                    if government.treasury >= work_wage:
                        government.treasury -= work_wage
                        u_agent.cash += work_wage
                        civic_cost += work_wage
                        # Repair district safety
                        if u_agent.district_id in districts:
                            dist = districts[u_agent.district_id]
                            dist.safety_score = min(1.0, dist.safety_score + 0.02)
                pol.daily_cost = civic_cost
                government.daily_public_works_paid = civic_cost
                government.daily_expenditures += civic_cost

            elif pol.policy_type == PolicyType.ANTI_CORRUPTION_CRACKDOWN:
                # Administrative audit cost suppresses corruption index
                audit_fee = 50.0
                if government.treasury >= audit_fee:
                    government.treasury -= audit_fee
                    government.daily_expenditures += audit_fee
                    pol.daily_cost = audit_fee
                    government.corruption_index = max(
                        0.01, round(government.corruption_index * 0.95, 4)
                    )

            elif pol.policy_type == PolicyType.AUSTERITY:
                # Freeze welfare and reduce non-critical expenditures
                pol.daily_cost = 0.0

        return expired_ids

    def evaluate_auto_governance(
        self,
        government: MunicipalGovernment,
        avg_favorability: float,
        avg_unrest: float,
        rioting_count: int,
        cpi: float,
        current_tick: int,
        rng: random.Random,
    ) -> list[ActivePolicy]:
        """
        Autonomous Governance AI: The municipal leadership enacts emergency policies
        in response to social distress, protests, inflation shocks, or fiscal deficits.
        """
        new_policies: list[ActivePolicy] = []

        # 1. Food Price Inflation / Starvation Crisis Response
        if (
            cpi > 120.0
            and "pol_food_subsidy" not in self.active_policies
            and government.treasury >= 15_000.0
        ):
            pol = ActivePolicy(
                policy_id="pol_food_subsidy",
                policy_type=PolicyType.FOOD_SUBSIDY,
                description="Emergency Municipal Food Price Subsidy (25% co-pay)",
                magnitude=0.25,
                start_tick=current_tick,
                duration_days=30,
            )
            self.enact_policy(pol)
            new_policies.append(pol)

        # 2. Civil Unrest or Riots Outbreak Response
        if (
            (rioting_count > 0 or avg_unrest > 0.50)
            and "pol_emergency_stimulus" not in self.active_policies
            and government.treasury >= 10_000.0
        ):
            pol = ActivePolicy(
                policy_id="pol_emergency_stimulus",
                policy_type=PolicyType.WELFARE_STIMULUS,
                description="Civil Peace Emergency Welfare Relief Grant (35 C)",
                magnitude=35.0,
                start_tick=current_tick,
                duration_days=14,
            )
            self.enact_policy(pol)
            new_policies.append(pol)

        # 3. High Unemployment & Deteriorating Infrastructure Response
        if (
            avg_unrest > 0.40
            and "pol_public_works" not in self.active_policies
            and government.treasury >= 15_000.0
        ):
            pol = ActivePolicy(
                policy_id="pol_public_works",
                policy_type=PolicyType.PUBLIC_WORKS,
                description="Civic Infrastructure Employment Program (20 C/day)",
                magnitude=20.0,
                start_tick=current_tick,
                duration_days=30,
            )
            self.enact_policy(pol)
            new_policies.append(pol)

        # 4. Anti-Corruption Inquiry Response
        if (
            government.corruption_index >= 0.12
            and "pol_anti_corruption" not in self.active_policies
            and government.treasury >= 5_000.0
        ):
            pol = ActivePolicy(
                policy_id="pol_anti_corruption",
                policy_type=PolicyType.ANTI_CORRUPTION_CRACKDOWN,
                description="Independent Public Ethics & Anti-Graft Audit",
                magnitude=0.50,
                start_tick=current_tick,
                duration_days=20,
            )
            self.enact_policy(pol)
            new_policies.append(pol)

        # 5. Fiscal Insolvency / Austerity Trigger
        if (
            government.treasury < 5_000.0
            and "pol_austerity" not in self.active_policies
        ):
            pol = ActivePolicy(
                policy_id="pol_austerity",
                policy_type=PolicyType.AUSTERITY,
                description="Emergency Fiscal Consolidation & Spending Freeze",
                magnitude=0.30,
                start_tick=current_tick,
                duration_days=45,
            )
            self.enact_policy(pol)
            new_policies.append(pol)

        return new_policies

    def to_dict(self) -> dict[str, Any]:
        return {k: v.to_dict() for k, v in self.active_policies.items()}
