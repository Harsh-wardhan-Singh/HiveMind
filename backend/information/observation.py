"""HIVEMIND Bounded Knowledge & Masked Observation Module."""

import random
from dataclasses import dataclass, field
from typing import Any

from backend.agents.agent import Agent
from backend.agents.roles import RoleType


@dataclass
class ObservationPacket:
    """
    Masked, noisy, role-bounded point-in-time observation packet for an agent.
    Agents never query global ground-truth state directly.
    """

    agent_id: str
    tick: int
    personal_ledger: dict[str, Any]
    home_district_id: str
    known_districts: dict[str, dict[str, float]] = field(default_factory=dict)
    known_companies: dict[str, dict[str, Any]] = field(default_factory=dict)
    read_headlines: list[dict[str, Any]] = field(default_factory=list)
    known_rumors: list[dict[str, Any]] = field(default_factory=list)
    information_tier: str = "baseline"

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "tick": self.tick,
            "information_tier": self.information_tier,
            "personal_ledger": self.personal_ledger,
            "home_district_id": self.home_district_id,
            "known_districts": self.known_districts,
            "known_companies": self.known_companies,
            "read_headlines": self.read_headlines,
            "known_rumors": self.known_rumors,
        }


def get_agent_information_tier(agent: Agent) -> tuple[str, float, float, int]:
    """
    Determine agent's information access bandwidth based on societal role and education.
    Returns (tier_name, local_noise_sigma, distant_noise_sigma, visible_districts_count).
    """
    edu_discount = max(0.5, 1.0 - 0.15 * agent.education_level)

    if agent.role in (
        RoleType.MAYOR,
        RoleType.INVESTOR,
        RoleType.RESEARCHER,
        RoleType.BUSINESS_OWNER,
    ):
        # Elite Information Access: Full city visibility, low observation error
        return "elite", 0.01 * edu_discount, 0.05 * edu_discount, 10
    elif agent.role in (
        RoleType.ENGINEER,
        RoleType.TEACHER,
        RoleType.HEALTHCARE_WORKER,
        RoleType.SKILLED_WORKER,
    ):
        # Professional Tier: Regional visibility, moderate noise
        return "professional", 0.02 * edu_discount, 0.10 * edu_discount, 5
    else:
        # Baseline / Working Tier: Hyper-local visibility, high distant noise
        return "baseline", 0.03 * edu_discount, 0.22 * edu_discount, 2


def generate_agent_observation(
    agent: Agent,
    world_state: Any,
    rng: random.Random,
    headlines: list[dict[str, Any]] | None = None,
    rumors: list[dict[str, Any]] | None = None,
) -> ObservationPacket:
    """
    Generate a masked observation packet tailored to an individual agent's bounded horizon.
    """
    tier_name, sigma_local, sigma_distant, max_districts = get_agent_information_tier(
        agent
    )

    # 1. Personal Financial & Physical Ledger (Exact ground truth of self)
    personal_ledger = {
        "cash": round(agent.cash, 2),
        "debt": round(agent.debt, 2),
        "bank_deposit": round(agent.bank_deposit, 2),
        "bank_loan": round(agent.bank_loan, 2),
        "portfolio": dict(agent.portfolio),
        "health": round(agent.health, 4),
        "last_tax_paid": round(agent.last_tax_paid, 2),
        "public_help_received": round(agent.public_help_received, 2),
        "favorability": round(agent.favorability, 4),
        "unrest": round(agent.unrest, 4),
    }

    # 2. Local & Distant District Market Perception
    known_districts: dict[str, dict[str, float]] = {}
    district_ids = list(world_state.districts.keys())

    # Always knows home district
    allowed_district_ids = [agent.district_id]

    # If employed, also knows employer's district
    if agent.employer_id and agent.employer_id in world_state.companies:
        emp_dist = world_state.companies[agent.employer_id].district_id
        if emp_dist not in allowed_district_ids:
            allowed_district_ids.append(emp_dist)

    # Add other reachable districts up to max_districts
    for d_id in district_ids:
        if len(allowed_district_ids) >= max_districts:
            break
        if d_id not in allowed_district_ids:
            allowed_district_ids.append(d_id)

    # Construct perceived noisy prices and conditions
    for d_id in allowed_district_ids:
        if d_id not in world_state.districts:
            continue
        dist = world_state.districts[d_id]
        is_home = d_id == agent.district_id
        sigma = sigma_local if is_home else sigma_distant

        perceived_prices = {}
        for c_type, true_price in world_state.market.prices.items():
            noise = rng.gauss(0.0, sigma)
            perceived_p = max(1.0, round(true_price * (1.0 + noise), 2))
            c_key = c_type.value if hasattr(c_type, "value") else str(c_type)
            perceived_prices[c_key] = perceived_p

        safety_noise = rng.gauss(0.0, sigma * 0.5)
        perceived_safety = max(
            0.0, min(1.0, round(dist.safety_score + safety_noise, 4))
        )

        known_districts[d_id] = {
            "name": dist.name,
            "rent": dist.rent,
            "perceived_safety": perceived_safety,
            "perceived_prices": perceived_prices,
            "is_home": is_home,
        }

    # 3. Known Local Companies
    known_companies: dict[str, dict[str, Any]] = {}
    for comp in world_state.companies.values():
        if (
            comp.district_id == agent.district_id
            or comp.id == agent.employer_id
            or tier_name == "elite"
        ):
            known_companies[comp.id] = {
                "name": comp.name,
                "ticker": comp.ticker,
                "target_wage": comp.target_wage,
                "district_id": comp.district_id,
            }

    # 4. News Headlines & Rumors bounded selection
    # More educated/open agents read more media headlines
    p = agent.personality
    read_count = max(1, int(1 + agent.education_level + 2 * p.openness))
    selected_headlines = (headlines or [])[:read_count]
    selected_rumors = (rumors or [])[:3]

    return ObservationPacket(
        agent_id=agent.id,
        tick=world_state.clock.current_tick,
        personal_ledger=personal_ledger,
        home_district_id=agent.district_id,
        known_districts=known_districts,
        known_companies=known_companies,
        read_headlines=selected_headlines,
        known_rumors=selected_rumors,
        information_tier=tier_name,
    )
