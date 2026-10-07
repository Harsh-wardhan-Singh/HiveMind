"""HIVEMIND Society Harmony Index, Interpersonal Distrust & Rebellion Feedback Module."""

from dataclasses import dataclass
from typing import Any

from backend.information.rumors import Rumor
from backend.society.relationships import RelationshipGraph


@dataclass
class SocietyHarmonyTracker:
    """
    Authoritative tracker of societal cohesion, mutual trust, and polarization.
    Disharmony erodes interpersonal trust among citizens and incites civil rebellion/riots.
    """

    harmony_index: float = (
        0.75  # [0.0 (Civil War / Chaos) to 1.0 (Harmonious Utopian Solidarity)]
    )
    interpersonal_distrust: float = 0.25  # Inverted trust metric [0.0, 1.0]
    disinformation_index: float = 0.0  # Toxic rumor penalty [0.0, 1.0]

    def update_harmony(
        self,
        world_state: Any,
        active_rumors: dict[str, Rumor],
        relationships: RelationshipGraph,
    ) -> tuple[float, float, float]:
        """
        Evaluate current society harmony, apply trust erosion feedback,
        and calculate the civil rebellion/unrest amplifier.
        Returns (harmony_index, interpersonal_distrust, unrest_penalty).
        """
        metrics = world_state.metrics
        govt = world_state.government

        # 1. Disinformation penalty from viral, fabricated rumors
        disinfo_penalty = 0.0
        if active_rumors:
            total_toxic = sum(
                r.intensity * (1.0 - r.veracity) for r in active_rumors.values()
            )
            disinfo_penalty = min(0.60, total_toxic * 0.15)
        self.disinformation_index = round(disinfo_penalty, 4)

        # 2. Civic approval & political legitimacy [0.0, 1.0]
        approval_score = metrics.approval_rating / 100.0

        # 3. Civil peace score (absence of unrest and active riots) [0.0, 1.0]
        unrest_score = metrics.city_unrest
        riot_penalty = 0.25 if metrics.rioting_districts_count > 0 else 0.0
        civil_peace = max(0.0, 1.0 - unrest_score - riot_penalty)

        # 4. Governance integrity & absence of corruption [0.0, 1.0]
        integrity_score = max(0.0, 1.0 - govt.corruption_index * 2.0)

        # 5. Baseline interpersonal social network trust [0.0, 1.0]
        mean_social_trust = relationships.average_trust

        # Composite Society Harmony Index
        raw_harmony = (
            0.25 * approval_score
            + 0.25 * civil_peace
            + 0.20 * integrity_score
            + 0.20 * mean_social_trust
            - 0.15 * disinfo_penalty
            + 0.05  # Societal resilience buffer
        )

        clamped_harmony = max(0.0, min(1.0, raw_harmony))
        # Smooth day-to-day transition: 80% persistence, 20% fresh condition
        smoothed_harmony = round(0.80 * self.harmony_index + 0.20 * clamped_harmony, 4)
        self.harmony_index = smoothed_harmony
        self.interpersonal_distrust = round(1.0 - self.harmony_index, 4)

        # 6. Interpersonal Distrust Feedback Loop:
        # If harmony drops below 0.50, mutual distrust erodes social network relationships!
        if self.harmony_index < 0.50:
            erosion_rate = (self.harmony_index - 0.50) * 0.005  # Negative delta
            relationships.modulate_trust(erosion_rate)
        elif self.harmony_index > 0.70:
            # High harmony slowly rebuilds social trust
            relationships.modulate_trust(0.001)

        # 7. Rebellion & Riot Feedback Loop:
        # When harmony is low, the deficit directly fuels citizen unrest and rebellion
        unrest_penalty = (
            max(0.0, (0.50 - self.harmony_index) * 0.30)
            if self.harmony_index < 0.50
            else 0.0
        )

        return (
            self.harmony_index,
            self.interpersonal_distrust,
            round(unrest_penalty, 4),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "harmony_index": round(self.harmony_index, 4),
            "interpersonal_distrust": round(self.interpersonal_distrust, 4),
            "disinformation_index": round(self.disinformation_index, 4),
        }
