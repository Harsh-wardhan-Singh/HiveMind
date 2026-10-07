"""HIVEMIND Demographic Lifecycle & Gompertz-Makeham Actuarial Mortality Model."""

import math
import random
from enum import Enum


class LifeStage(str, Enum):
    INFANT = "INFANT"  # 0 - 5 years
    CHILD_STUDENT = "CHILD_STUDENT"  # 6 - 17 years
    EARLY_CAREER = "EARLY_CAREER"  # 18 - 22 years
    WORKING_AGE = "WORKING_AGE"  # 23 - 59 years
    LATE_CAREER = "LATE_CAREER"  # 60 - 69 years
    RETIRED = "RETIRED"  # 70+ years


def get_life_stage(age_years: int) -> LifeStage:
    """Derive official life stage from age in years."""
    if age_years <= 5:
        return LifeStage.INFANT
    elif age_years <= 17:
        return LifeStage.CHILD_STUDENT
    elif age_years <= 22:
        return LifeStage.EARLY_CAREER
    elif age_years <= 59:
        return LifeStage.WORKING_AGE
    elif age_years <= 69:
        return LifeStage.LATE_CAREER
    else:
        return LifeStage.RETIRED


def calculate_gompertz_makeham_daily_hazard(
    age_years: float, health: float = 1.0
) -> float:
    """
    Calculate the daily mortality hazard rate using Gompertz-Makeham law:
    mu(x) = A + B * exp(C * x)
    where A is age-independent baseline hazard, and B/C drive exponential aging mortality.
    Scaled by health status when health < 0.20.
    """
    # Standard calibrated annual constants scaled to daily
    A = 0.0001 / 365.25  # Baseline accident / environmental hazard
    B = 0.000045 / 365.25  # Gompertz base
    C = 0.082  # Gompertz exponential factor

    base_hazard = A + B * math.exp(C * min(age_years, 110.0))

    # Health multiplier: severe impairment exponentially raises mortality risk
    if health < 0.20:
        health_penalty = 1.0 + 10.0 * (0.20 - health)
        base_hazard *= health_penalty

    # Convert daily hazard rate mu to probability of dying on this tick: P(death) = 1 - exp(-mu)
    daily_p_death = 1.0 - math.exp(-base_hazard)
    return max(0.0, min(1.0, daily_p_death))


def evaluate_daily_mortality(
    age_years: float, health: float, rng: random.Random
) -> bool:
    """
    Returns True if agent dies on this tick according to Gompertz-Makeham hazard probability.
    """
    p_death = calculate_gompertz_makeham_daily_hazard(age_years, health)
    return rng.random() < p_death

