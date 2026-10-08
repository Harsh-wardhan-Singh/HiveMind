from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from backend.agents.agent import Agent
from backend.agents.roles import RoleType
from backend.politics.candidates import Candidate, PoliticalPlatform
from backend.politics.government import MunicipalGovernment

if TYPE_CHECKING:
    from backend.simulation.districts import District


@dataclass
class ElectionResult:
    """Certified result of a municipal election."""

    tick: int
    winner_id: str
    winner_name: str
    winner_platform: str
    is_incumbent_reelected: bool
    total_votes_cast: int
    vote_tallies: dict[str, int]
    candidates: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tick": self.tick,
            "winner_id": self.winner_id,
            "winner_name": self.winner_name,
            "winner_platform": self.winner_platform,
            "is_incumbent_reelected": self.is_incumbent_reelected,
            "total_votes_cast": self.total_votes_cast,
            "vote_tallies": self.vote_tallies,
            "candidates": self.candidates,
        }


def nominate_candidates(
    sitting_mayor_id: str,
    agents: dict[str, Agent],
    government: MunicipalGovernment,
    rng: random.Random,
) -> list[Candidate]:
    """
    Generate the ballot: sitting Mayor (if alive) plus 2 to 3 diverse challengers
    drawn from active adult citizens representing distinct political platforms.
    """
    candidates: list[Candidate] = []

    # 1. Incumbent Mayor
    sitting_mayor = agents.get(sitting_mayor_id)
    if sitting_mayor and sitting_mayor.alive:
        p = sitting_mayor.personality
        incumbent_charisma = round(0.5 * p.extraversion + 0.5 * p.agreeableness, 4)
        incumbent_integrity = round(
            p.conscientiousness * (1.0 - government.corruption_index * 0.5), 4
        )
        incumbent_platform = PoliticalPlatform(
            name="Incumbent Civic Continuity",
            income_tax_mid=government.tax_rates.income_tax_mid,
            corporate_tax=government.tax_rates.corporate_tax,
            welfare_generosity=0.45,
            anti_corruption_pledge=max(0.1, 1.0 - government.corruption_index),
            infrastructure_investment=0.50,
        )
        candidates.append(
            Candidate(
                candidate_id="cand_incumbent",
                agent_id=sitting_mayor.id,
                name=f"Mayor ({sitting_mayor.id})",
                role="MAYOR",
                platform=incumbent_platform,
                charisma=incumbent_charisma,
                integrity=incumbent_integrity,
                is_incumbent=True,
            )
        )

    # 2. Eligible challengers: adult citizens (age >= 18)
    eligible = [
        a
        for a in agents.values()
        if a.alive and a.age_years >= 18 and a.id != sitting_mayor_id
    ]
    if not eligible:
        return candidates

    # Platform blueprints
    platform_blueprints = [
        (
            "Progressive Welfare & Public Relief",
            PoliticalPlatform(
                name="Progressive Welfare & Public Relief",
                income_tax_mid=0.12,
                corporate_tax=0.22,
                welfare_generosity=0.85,
                anti_corruption_pledge=0.80,
                infrastructure_investment=0.60,
            ),
            [
                RoleType.HEALTHCARE_WORKER,
                RoleType.TEACHER,
                RoleType.MANUAL_WORKER,
                RoleType.UNEMPLOYED,
            ],
        ),
        (
            "Free Market & Low Tax Enterprise",
            PoliticalPlatform(
                name="Free Market & Low Tax Enterprise",
                income_tax_mid=0.06,
                corporate_tax=0.08,
                welfare_generosity=0.20,
                anti_corruption_pledge=0.50,
                infrastructure_investment=0.40,
            ),
            [RoleType.BUSINESS_OWNER, RoleType.INVESTOR],
        ),
        (
            "Technocratic Infrastructure & Law",
            PoliticalPlatform(
                name="Technocratic Infrastructure & Law",
                income_tax_mid=0.10,
                corporate_tax=0.15,
                welfare_generosity=0.50,
                anti_corruption_pledge=0.75,
                infrastructure_investment=0.85,
            ),
            [RoleType.ENGINEER, RoleType.RESEARCHER, RoleType.SKILLED_WORKER],
        ),
    ]

    # Select challengers prioritizing matching roles
    assigned_agent_ids: set[str] = {sitting_mayor_id}
    for idx, (plat_name, plat_obj, preferred_roles) in enumerate(
        platform_blueprints, start=1
    ):
        matching = [
            a
            for a in eligible
            if a.role in preferred_roles and a.id not in assigned_agent_ids
        ]
        chosen = matching[0] if matching else None
        if not chosen:
            remaining = [a for a in eligible if a.id not in assigned_agent_ids]
            if remaining:
                chosen = remaining[rng.randint(0, len(remaining) - 1)]

        if chosen:
            assigned_agent_ids.add(chosen.id)
            p = chosen.personality
            charisma = round(0.5 * p.extraversion + 0.5 * p.agreeableness, 4)
            integrity = round(0.6 * p.conscientiousness + 0.4 * p.social_trust, 4)
            candidates.append(
                Candidate(
                    candidate_id=f"cand_challenger_{idx}",
                    agent_id=chosen.id,
                    name=f"Candidate {chosen.id} ({chosen.role.value if hasattr(chosen.role, 'value') else str(chosen.role)})",
                    role=(
                        chosen.role.value
                        if hasattr(chosen.role, "value")
                        else str(chosen.role)
                    ),
                    platform=plat_obj,
                    charisma=charisma,
                    integrity=integrity,
                    is_incumbent=False,
                )
            )

    return candidates


def evaluate_voter_utility(
    voter: Agent,
    candidate: Candidate,
    sitting_corruption: float,
    rng: random.Random,
) -> float:
    """
    Evaluate voter utility for a specific candidate based on economic self-interest,
    ideological platform alignment, candidate charisma, and integrity.
    """
    p = voter.personality
    plat = candidate.platform

    if candidate.is_incumbent:
        # Incumbent utility is anchored by voter's actual personal favorability
        base_utility = voter.favorability * 1.5
        # Penalize if sitting corruption was severe
        base_utility -= sitting_corruption * (0.8 + 0.4 * p.conscientiousness)
    else:
        # Challenger evaluation based on platform alignment with voter situation
        utility_welfare = 0.0
        if voter.cash < 800.0 or voter.employer_id is None:
            utility_welfare = plat.welfare_generosity * 0.40
        else:
            # Wealthy voters dislike excessive welfare tax burdens
            utility_welfare = (1.0 - plat.welfare_generosity) * 0.20

        utility_tax = 0.0
        if (
            voter.role in (RoleType.BUSINESS_OWNER, RoleType.INVESTOR)
            or voter.cash > 3000.0
        ):
            # Low corporate and income tax strongly appeal to wealthy and owners
            utility_tax = (0.25 - plat.corporate_tax) * 2.0 + (
                0.20 - plat.income_tax_mid
            ) * 2.0
        else:
            utility_tax = (0.15 - plat.income_tax_mid) * 1.0

        # Conscientious voters value anti-corruption pledges and integrity
        utility_integrity = (
            candidate.integrity * 0.25
            + plat.anti_corruption_pledge * 0.25 * p.conscientiousness
        )

        # Neurotic or security-seeking voters value infrastructure investment
        utility_infra = plat.infrastructure_investment * 0.20 * p.neuroticism

        base_utility = (
            0.30 + utility_welfare + utility_tax + utility_integrity + utility_infra
        )

    # Charisma bonus
    charisma_bonus = candidate.charisma * 0.15

    # Small individual perception noise
    noise = rng.uniform(-0.05, 0.05)

    return base_utility + charisma_bonus + noise


def conduct_election(
    agents: dict[str, Agent],
    districts: dict[str, District],
    government: MunicipalGovernment,
    current_tick: int,
    rng: random.Random,
) -> ElectionResult:
    """
    Conduct a city-wide democratic election.
    Every living adult citizen (age >= 18) casts a secret ballot for their preferred candidate.
    Returns the certified ElectionResult.
    """
    candidates = nominate_candidates(
        sitting_mayor_id=government.current_mayor_id,
        agents=agents,
        government=government,
        rng=rng,
    )

    if not candidates:
        return ElectionResult(
            tick=current_tick,
            winner_id=government.current_mayor_id,
            winner_name="Incumbent Default",
            winner_platform="Continuity",
            is_incumbent_reelected=True,
            total_votes_cast=0,
            vote_tallies={},
        )

    # If only one candidate on ballot
    if len(candidates) == 1:
        winner = candidates[0]
        return ElectionResult(
            tick=current_tick,
            winner_id=winner.agent_id,
            winner_name=winner.name,
            winner_platform=winner.platform.name,
            is_incumbent_reelected=winner.is_incumbent,
            total_votes_cast=0,
            vote_tallies={winner.candidate_id: 0},
            candidates=[c.to_dict() for c in candidates],
        )

    # Voting tally
    vote_tallies: dict[str, int] = {c.candidate_id: 0 for c in candidates}
    total_votes = 0

    # Adult citizens cast ballots
    for voter in agents.values():
        if not voter.alive or voter.age_years < 18:
            continue

        best_cand: Candidate | None = None
        best_util = -999.0

        for cand in candidates:
            util = evaluate_voter_utility(
                voter=voter,
                candidate=cand,
                sitting_corruption=government.corruption_index,
                rng=rng,
            )
            if util > best_util:
                best_util = util
                best_cand = cand

        if best_cand:
            vote_tallies[best_cand.candidate_id] += 1
            total_votes += 1

    # Determine winner (plurality)
    sorted_candidates = sorted(
        candidates, key=lambda c: vote_tallies[c.candidate_id], reverse=True
    )
    winner = sorted_candidates[0]

    return ElectionResult(
        tick=current_tick,
        winner_id=winner.agent_id,
        winner_name=winner.name,
        winner_platform=winner.platform.name,
        is_incumbent_reelected=winner.is_incumbent,
        total_votes_cast=total_votes,
        vote_tallies=vote_tallies,
        candidates=[c.to_dict() for c in candidates],
    )


def apply_election_result(
    result: ElectionResult,
    government: MunicipalGovernment,
    agents: dict[str, Agent],
) -> tuple[bool, str]:
    """
    Ratify election outcome.
    If a challenger wins, effectuates a democratic transfer of power:
    - Retires former mayor to standard civilian profession.
    - Elevates winner to RoleType.MAYOR.
    - Updates municipal tax rates and curtails corruption per the winner's platform.
    Returns (transferred_power, message).
    """
    government.total_elections_held += 1
    government.consecutive_low_favorability_days = 0

    if result.is_incumbent_reelected:
        return False, f"Mayor re-elected with platform: {result.winner_platform}."

    # Power transition
    old_mayor_id = government.current_mayor_id
    new_mayor_id = result.winner_id

    # Demote previous mayor if alive
    if old_mayor_id and old_mayor_id in agents and agents[old_mayor_id].alive:
        agents[old_mayor_id].role = RoleType.RESEARCHER

    # Elevate new mayor
    if new_mayor_id in agents:
        agents[new_mayor_id].role = RoleType.MAYOR
        government.current_mayor_id = new_mayor_id

    # Enact new administration's policy platform
    for c_info in result.candidates:
        if c_info.get("agent_id") == new_mayor_id:
            plat = c_info.get("platform", {})
            if "income_tax_mid" in plat:
                government.tax_rates.income_tax_mid = plat["income_tax_mid"]
            if "corporate_tax" in plat:
                government.tax_rates.corporate_tax = plat["corporate_tax"]
            # Anti-corruption reform slashes existing graft
            anti_corr = plat.get("anti_corruption_pledge", 0.5)
            government.corruption_index = max(
                0.01, round(government.corruption_index * (1.0 - anti_corr * 0.6), 4)
            )
            break

    return (
        True,
        f"New Mayor {new_mayor_id} inaugurated! Platform: {result.winner_platform}.",
    )
