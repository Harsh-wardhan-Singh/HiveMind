"""HIVEMIND Rumor Network Diffusion, Drift & Heterogeneous Sharing Propensity Module."""

import random
from dataclasses import dataclass
from typing import Any

from backend.agents.agent import Agent
from backend.society.relationships import RelationshipGraph


@dataclass
class Rumor:
    """An organic informal rumor or piece of hearsay traversing social edges."""

    rumor_id: str
    topic: str
    headline: str
    intensity: float  # [0.0 (Mild Curiosity) to 1.0 (Panic / Outrage)]
    veracity: float  # [0.0 (Pure Fabricated Fiction) to 1.0 (Factual Ground Truth)]
    origin_tick: int
    transmission_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "rumor_id": self.rumor_id,
            "topic": self.topic,
            "headline": self.headline,
            "intensity": round(self.intensity, 4),
            "veracity": round(self.veracity, 4),
            "origin_tick": self.origin_tick,
            "transmissions": self.transmission_count,
        }


def calculate_sharing_chance(agent: Agent, rumor: Rumor) -> float:
    """
    Calculate an agent's individual propensity to spread a rumor [0.05, 0.95].
    Modulated by Big-Five personality traits:
    - High Extraversion: more social conversations, shares easily.
    - High Neuroticism: amplified anxiety, eagerly spreads alarming rumors.
    - High Conscientiousness: fact-checks and withholds dubious/false rumors.
    - Low Agreeableness / High Ambition: spreads divisive rumors strategically.
    """
    p = agent.personality

    base_chance = 0.20
    extraversion_boost = 0.35 * p.extraversion
    neurotic_panic = 0.25 * p.neuroticism * rumor.intensity
    conscientious_filter = 0.25 * p.conscientiousness * (1.0 - rumor.veracity)

    sharing_prob = (
        base_chance + extraversion_boost + neurotic_panic - conscientious_filter
    )
    return max(0.05, min(0.95, round(sharing_prob, 4)))


class RumorEngine:
    """Simulates word-of-mouth diffusion, distortion drift, and belief accumulation."""

    def __init__(self) -> None:
        self.active_rumors: dict[str, Rumor] = {}
        # Mapping: agent_id -> {topic: belief_level [0.0, 1.0]}
        self.agent_beliefs: dict[str, dict[str, float]] = {}

    def spawn_rumor(
        self,
        topic: str,
        headline: str,
        intensity: float,
        veracity: float,
        origin_tick: int,
        initial_carriers: list[str],
    ) -> Rumor:
        """Inject a new rumor into initial carrier agents."""
        rumor_id = f"rumor_{origin_tick:04d}_{topic.lower()}"
        rumor = Rumor(
            rumor_id=rumor_id,
            topic=topic,
            headline=headline,
            intensity=intensity,
            veracity=veracity,
            origin_tick=origin_tick,
        )
        self.active_rumors[rumor_id] = rumor

        for agent_id in initial_carriers:
            if agent_id not in self.agent_beliefs:
                self.agent_beliefs[agent_id] = {}
            self.agent_beliefs[agent_id][topic] = intensity

        return rumor

    def diffuse_rumors(
        self,
        agents: dict[str, Agent],
        relationships: RelationshipGraph,
        current_tick: int,
        rng: random.Random,
        alpha: float = 0.40,
    ) -> list[dict[str, Any]]:
        """
        Execute one daily word-of-mouth diffusion cycle along social graph edges.
        Belief update follows trust-weighted formula with transmission distortion:
        Belief_j = (1 - alpha * T_ij) * Belief_j + alpha * T_ij * (Belief_i + eta_ij)
        """
        transmissions: list[dict[str, Any]] = []

        # Iterate over living agents who know active rumors
        for sender_id, beliefs in list(self.agent_beliefs.items()):
            sender = agents.get(sender_id)
            if not sender or not sender.alive:
                continue

            # Find social network neighbors
            neighbors = relationships.get_neighbors(sender_id)
            if not neighbors:
                continue

            for rumor_id, rumor in list(self.active_rumors.items()):
                if rumor.topic not in beliefs or beliefs[rumor.topic] < 0.15:
                    continue

                # Check heterogeneous sharing propensity
                p_share = calculate_sharing_chance(sender, rumor)
                if rng.random() > p_share:
                    continue

                # Share with a contact
                receiver_id = neighbors[rng.randint(0, len(neighbors) - 1)]
                receiver = agents.get(receiver_id)
                if not receiver or not receiver.alive:
                    continue

                # Trust along social edge
                edge = relationships.get_edge(sender_id, receiver_id)
                trust_weight = edge.trust if edge else 0.50

                # Transmission distortion drift
                drift = rng.gauss(0.0, 0.04)
                sender_belief = beliefs[rumor.topic]

                if receiver_id not in self.agent_beliefs:
                    self.agent_beliefs[receiver_id] = {}
                receiver_belief = self.agent_beliefs[receiver_id].get(rumor.topic, 0.0)

                # Trust-weighted adoption
                updated_belief = (1.0 - alpha * trust_weight) * receiver_belief + (
                    alpha * trust_weight * (sender_belief + drift)
                )
                updated_belief = max(0.0, min(1.0, round(updated_belief, 4)))
                self.agent_beliefs[receiver_id][rumor.topic] = updated_belief

                rumor.transmission_count += 1
                transmissions.append(
                    {
                        "rumor_id": rumor.rumor_id,
                        "topic": rumor.topic,
                        "sender": sender_id,
                        "receiver": receiver_id,
                        "receiver_belief": updated_belief,
                    }
                )

        # Decay stale rumors older than 35 ticks
        for r_id, r in list(self.active_rumors.items()):
            if current_tick - r.origin_tick > 35:
                del self.active_rumors[r_id]

        return transmissions

    def trigger_contextual_rumors(
        self,
        world_state: Any,
        rng: random.Random,
    ) -> list[Rumor]:
        """
        Organically generate contextual rumors when economic or political shocks occur.
        """
        spawned: list[Rumor] = []
        tick = world_state.clock.current_tick
        metrics = world_state.metrics
        alive_ids = [a.id for a in world_state.agents.values() if a.alive]

        if not alive_ids:
            return spawned

        # 1. Bank Run Rumor if bank loans exceed bank reserves or deposits drop
        if (
            metrics.total_bank_loans > metrics.bank_reserves
            and "rumor_bank_insolvency"
            not in [r.topic.lower() for r in self.active_rumors.values()]
        ):
            carriers = [alive_ids[rng.randint(0, len(alive_ids) - 1)] for _ in range(2)]
            r = self.spawn_rumor(
                topic="BANK_INSOLVENCY",
                headline="Rumor: Municipal Bank Facing Liquidity Depletion",
                intensity=0.75,
                veracity=0.40,
                origin_tick=tick,
                initial_carriers=carriers,
            )
            spawned.append(r)

        # 2. Food Scarcity Rumor if food price rises above 12 C
        food_price = world_state.market.prices.get(
            next(iter(world_state.market.prices.keys())), 10.0
        )
        if food_price > 12.0 and "food_scarcity" not in [
            r.topic.lower() for r in self.active_rumors.values()
        ]:
            carriers = [alive_ids[rng.randint(0, len(alive_ids) - 1)] for _ in range(3)]
            r = self.spawn_rumor(
                topic="FOOD_SCARCITY",
                headline="Hearsay: Severe Grain Shortages Expected Next Month",
                intensity=0.70,
                veracity=0.60,
                origin_tick=tick,
                initial_carriers=carriers,
            )
            spawned.append(r)

        # 3. Corruption Rumor if sitting government corruption is notable
        if world_state.government.corruption_index > 0.08 and "mayor_graft" not in [
            r.topic.lower() for r in self.active_rumors.values()
        ]:
            carriers = [alive_ids[rng.randint(0, len(alive_ids) - 1)] for _ in range(2)]
            r = self.spawn_rumor(
                topic="MAYOR_GRAFT",
                headline="Whispers: City Hall Officials Siphoning Public Treasury Funds",
                intensity=0.80,
                veracity=0.85,
                origin_tick=tick,
                initial_carriers=carriers,
            )
            spawned.append(r)

        return spawned

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_rumors_count": len(self.active_rumors),
            "rumors": [r.to_dict() for r in self.active_rumors.values()],
            "active_carriers_count": len(self.agent_beliefs),
        }
