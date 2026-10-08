from __future__ import annotations

import random
from typing import TYPE_CHECKING, Any

from backend.agents.agent import Agent
from backend.companies.company import Company
from backend.politics.government import MunicipalGovernment

if TYPE_CHECKING:
    from backend.simulation.districts import District


def evaluate_agent_unrest(
    agent: Agent,
    district_safety: float,
    corruption_index: float,
) -> float:
    """
    Calculate an individual agent's unrest score [0.0, 1.0].
    Low favorability, severe hunger, rampant corruption, high neuroticism,
    and low agreeableness intensify unrest and protest propensity.
    """
    if not agent.alive:
        agent.unrest = 0.0
        return 0.0

    p = agent.personality

    # Baseline discontent derived from low favorability
    discontent = max(0.0, 1.0 - agent.favorability)

    # Personality modulation: neuroticism amplifies agitation, agreeableness dampens it
    psych_mod = 0.70 + 0.50 * p.neuroticism - 0.30 * p.agreeableness

    # Hunger / starvation shock
    hunger_factor = 0.0
    if agent.health < 0.40:
        hunger_factor = (0.40 - agent.health) * 1.5

    # Poverty / unemployment friction
    poverty_factor = 0.0
    if agent.cash < 200.0 and agent.employer_id is None:
        poverty_factor = 0.25

    # Environmental danger / unsafe district
    danger_factor = max(0.0, (0.50 - district_safety) * 0.40)

    # Corruption outrage
    corruption_outrage = corruption_index * (0.6 + 0.4 * p.conscientiousness)

    raw_unrest = (
        0.40 * (discontent * psych_mod)
        + 0.25 * hunger_factor
        + 0.15 * poverty_factor
        + 0.10 * danger_factor
        + 0.10 * corruption_outrage
    )

    clamped_unrest = max(0.0, min(1.0, raw_unrest))
    # Smooth day-to-day transition (initialize directly if currently zero)
    if agent.unrest == 0.0:
        agent.unrest = round(clamped_unrest, 4)
    else:
        agent.unrest = round(0.70 * agent.unrest + 0.30 * clamped_unrest, 4)
    return agent.unrest


def evaluate_district_unrest(
    districts: dict[str, District],
    agents: dict[str, Agent],
    corruption_index: float,
    riot_threshold: float = 0.65,
) -> tuple[dict[str, float], list[str]]:
    """
    Evaluate unrest scores for all districts and detect newly erupting riots.
    Returns (district_unrest_scores, newly_rioting_district_ids).
    """
    unrest_scores: dict[str, float] = {}
    new_riots: list[str] = []

    # Group agents by district
    agents_by_district: dict[str, list[Agent]] = {d_id: [] for d_id in districts}
    for a in agents.values():
        if a.alive and a.district_id in agents_by_district:
            agents_by_district[a.district_id].append(a)

    for d_id, district in districts.items():
        local_agents = agents_by_district[d_id]
        if not local_agents:
            district.unrest_score = 0.0
            unrest_scores[d_id] = 0.0
            continue

        # Evaluate individual unrest
        total_agent_unrest = 0.0
        unemployed_count = 0
        for a in local_agents:
            u = evaluate_agent_unrest(
                agent=a,
                district_safety=district.safety_score,
                corruption_index=corruption_index,
            )
            total_agent_unrest += u
            if a.employer_id is None:
                unemployed_count += 1

        avg_agent_unrest = total_agent_unrest / len(local_agents)
        unemp_rate = unemployed_count / len(local_agents)
        danger = max(0.0, 1.0 - district.safety_score)

        # Composite district unrest score
        composite_unrest = 0.55 * avg_agent_unrest + 0.25 * danger + 0.20 * unemp_rate
        composite_unrest = min(1.0, max(0.0, composite_unrest))
        district.unrest_score = round(composite_unrest, 4)
        unrest_scores[d_id] = district.unrest_score

        # Check riot trigger
        if district.unrest_score >= riot_threshold:
            if not district.is_rioting:
                district.is_rioting = True
                district.riot_days = 1
                new_riots.append(d_id)
            else:
                district.riot_days += 1
        elif district.is_rioting:
            district.riot_days += 1

    return unrest_scores, new_riots


def process_active_riots(
    districts: dict[str, District],
    companies: dict[str, Company],
    agents: dict[str, Agent],
    government: MunicipalGovernment,
    rng: random.Random,
) -> dict[str, Any]:
    """
    Apply physical, commercial, and financial damage caused by active riots.
    - District safety plunges.
    - Local companies suffer commercial inventory looting/damage.
    - City incurs emergency infrastructure repair expenses.
    - Clashing agents face small health impacts.
    """
    total_looted_inventory = 0.0
    total_municipal_repairs = 0.0
    rioting_districts = [d for d in districts.values() if d.is_rioting]

    for dist in rioting_districts:
        # 1. District safety degradation
        dist.safety_score = max(0.05, round(dist.safety_score - 0.08, 4))

        # 2. Looting and supply chain destruction of local companies
        for comp in companies.values():
            if comp.district_id == dist.id and comp.solvency and comp.inventory > 10.0:
                loot_qty = round(min(comp.inventory * 0.15, 50.0), 2)
                comp.inventory -= loot_qty
                total_looted_inventory += loot_qty

        # 3. Municipal property damage repair costs
        repair_cost = 500.0
        if government.treasury >= repair_cost:
            government.treasury -= repair_cost
            government.daily_expenditures += repair_cost
            total_municipal_repairs += repair_cost

        # 4. Agent clash exposure
        for a in agents.values():
            if (
                a.alive
                and a.district_id == dist.id
                and a.unrest > 0.60
                and rng.random() < 0.20
            ):
                a.health = max(0.10, round(a.health - 0.015, 4))

    return {
        "rioting_districts_count": len(rioting_districts),
        "total_looted_inventory": total_looted_inventory,
        "total_municipal_repairs": total_municipal_repairs,
    }


def quell_district_riots(
    districts: dict[str, District],
    quell_threshold: float = 0.45,
) -> list[str]:
    """
    Check if conditions have de-escalated and extinguish quelled riots.
    Returns list of district IDs where riots ceased.
    """
    quelled: list[str] = []
    for d in districts.values():
        if d.is_rioting and d.unrest_score < quell_threshold:
            d.is_rioting = False
            d.riot_days = 0
            quelled.append(d.id)
    return quelled
