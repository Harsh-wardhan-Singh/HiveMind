from __future__ import annotations

from typing import TYPE_CHECKING

from backend.agents.agent import Agent

if TYPE_CHECKING:
    from backend.simulation.districts import District


def calculate_agent_favorability(
    agent: Agent,
    district: District | None,
    inflation_rate: float,
    corruption_index: float,
    has_recent_scandal: bool = False,
) -> float:
    """
    Evaluate an individual citizen's favorability of the sitting government [0.0, 1.0].

    Components:
    - Wealth Score (w_w = 0.20): cash buffer, employment status.
    - Food & Health Security (w_f = 0.25): biological health, absence of starvation.
    - Price Stability (w_p = 0.15): penalizes high positive inflation.
    - District Safety (w_s = 0.15): quality of living and security in home district.
    - Public Help Received (w_h = 0.10): boosts favorability if recently assisted.
    - Governance Integrity / Corruption (w_c = 0.15): penalizes corruption and graft,
      amplified for citizens with high conscientiousness and social trust.
    - Scandal Shock: immediate penalty if a corruption scandal was exposed.
    """
    if not agent.alive:
        return 0.0

    # 1. Wealth & Employment Score [0.0, 1.0]
    wealth_score = min(1.0, agent.cash / 3000.0)
    if agent.employer_id is not None:
        wealth_score = min(1.0, wealth_score + 0.15)
    elif agent.cash < 500.0:
        wealth_score = max(0.0, wealth_score - 0.20)

    # 2. Food & Health Security [0.0, 1.0]
    food_health_score = agent.health
    if agent.health < 0.30:
        food_health_score = max(0.0, agent.health * 0.5)

    # 3. Price Stability Score [0.0, 1.0]
    # Stable inflation around 0-2% is ideal; rapid inflation or deflation penalizes score
    inf_abs = abs(inflation_rate)
    price_stability = max(0.0, 1.0 - (inf_abs / 10.0))

    # 4. District Safety Score [0.0, 1.0]
    safety_score = district.safety_score if district else 0.5
    if district and district.is_rioting:
        safety_score = max(0.0, safety_score - 0.40)

    # 5. Public Help Factor [0.0, 1.0]
    help_factor = 0.0
    if agent.public_help_received > 0.0:
        help_factor = min(1.0, agent.public_help_received / 50.0)

    # 6. Corruption Penalty [0.0, 1.0]
    p = agent.personality
    moral_multiplier = 0.8 + 0.6 * p.conscientiousness + 0.4 * p.social_trust
    corruption_penalty = min(1.0, corruption_index * moral_multiplier)
    if has_recent_scandal:
        corruption_penalty = min(1.0, corruption_penalty + 0.25)

    # Weighted linear combination
    raw_favorability = (
        0.20 * wealth_score
        + 0.25 * food_health_score
        + 0.15 * price_stability
        + 0.15 * safety_score
        + 0.10 * help_factor
        - 0.15 * corruption_penalty
        + 0.10  # Baseline civic optimism
    )

    # Tax burden damping: if tax paid yesterday was significant relative to cash
    if agent.cash > 0.0 and agent.last_tax_paid > 0.0:
        tax_ratio = min(1.0, agent.last_tax_paid / (agent.cash + 1.0))
        if tax_ratio > 0.25:
            raw_favorability -= 0.05

    # Clamp to valid probability interval [0.0, 1.0]
    clamped_fav = max(0.0, min(1.0, raw_favorability))

    # Smooth day-to-day transition: 75% memory, 25% new sentiment
    smoothed = 0.75 * agent.favorability + 0.25 * clamped_fav
    agent.favorability = round(smoothed, 4)

    # Decay public help memory slightly each day
    agent.public_help_received = max(0.0, agent.public_help_received * 0.90)

    return agent.favorability


def update_all_favorability(
    agents: dict[str, Agent],
    districts: dict[str, District],
    inflation_rate: float,
    corruption_index: float,
    has_recent_scandal: bool = False,
) -> tuple[float, float]:
    """
    Update favorability ratings across all living agents.
    Returns (average_city_favorability, approval_rating_pct).
    """
    alive_agents = [a for a in agents.values() if a.alive]
    if not alive_agents:
        return 0.5, 50.0

    total_fav = 0.0
    approving_count = 0

    for agent in alive_agents:
        district = districts.get(agent.district_id)
        fav = calculate_agent_favorability(
            agent=agent,
            district=district,
            inflation_rate=inflation_rate,
            corruption_index=corruption_index,
            has_recent_scandal=has_recent_scandal,
        )
        total_fav += fav
        if fav >= 0.50:
            approving_count += 1

    avg_fav = total_fav / len(alive_agents)
    approval_rating = (approving_count / len(alive_agents)) * 100.0
    return round(avg_fav, 4), round(approval_rating, 2)
