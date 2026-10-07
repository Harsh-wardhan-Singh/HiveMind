"""HIVEMIND Agent Personality and Psychological Trait Model."""

import random
from dataclasses import dataclass


@dataclass
class Personality:
    """
    Five-Factor Model (OCEAN) + secondary behavioral tendencies.
    All scores are bounded in [0.0, 1.0].
    """

    openness: float  # O: Curiosity, creativity vs convention
    conscientiousness: float  # C: Organization, diligence, savings preference
    extraversion: float  # E: Social engagement, rumor sharing frequency
    agreeableness: float  # A: Social trust, cooperation, compliance
    neuroticism: float  # N: Emotional reactivity, panic response to price shocks

    risk_tolerance: float  # R: Propensity for risky investments or job shifts
    social_trust: float  # T: Baseline trust in news media and rumors
    ambition: float  # M: Career drive and reservation wage multiplier

    def to_dict(self) -> dict[str, float]:
        return {
            "openness": round(self.openness, 4),
            "conscientiousness": round(self.conscientiousness, 4),
            "extraversion": round(self.extraversion, 4),
            "agreeableness": round(self.agreeableness, 4),
            "neuroticism": round(self.neuroticism, 4),
            "risk_tolerance": round(self.risk_tolerance, 4),
            "social_trust": round(self.social_trust, 4),
            "ambition": round(self.ambition, 4),
        }


def generate_personality(rng: random.Random) -> Personality:
    """
    Generate a deterministic personality profile with realistic normal distributions
    truncated to [0.0, 1.0].
    """

    def sample_truncated_normal(mean: float = 0.5, std: float = 0.15) -> float:
        val = rng.gauss(mean, std)
        return max(0.05, min(0.95, val))

    return Personality(
        openness=sample_truncated_normal(0.50, 0.18),
        conscientiousness=sample_truncated_normal(0.55, 0.15),
        extraversion=sample_truncated_normal(0.50, 0.16),
        agreeableness=sample_truncated_normal(0.60, 0.14),
        neuroticism=sample_truncated_normal(0.45, 0.17),
        risk_tolerance=sample_truncated_normal(0.40, 0.18),
        social_trust=sample_truncated_normal(0.55, 0.15),
        ambition=sample_truncated_normal(0.50, 0.18),
    )

