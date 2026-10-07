"""Unit tests for Demographic Lifecycle and Gompertz-Makeham Mortality."""

import random

from backend.agents.lifecycle import (
    LifeStage,
    calculate_gompertz_makeham_daily_hazard,
    evaluate_daily_mortality,
    get_life_stage,
)


def test_life_stages():
    assert get_life_stage(0) == LifeStage.INFANT
    assert get_life_stage(5) == LifeStage.INFANT
    assert get_life_stage(6) == LifeStage.CHILD_STUDENT
    assert get_life_stage(17) == LifeStage.CHILD_STUDENT
    assert get_life_stage(18) == LifeStage.EARLY_CAREER
    assert get_life_stage(22) == LifeStage.EARLY_CAREER
    assert get_life_stage(23) == LifeStage.WORKING_AGE
    assert get_life_stage(59) == LifeStage.WORKING_AGE
    assert get_life_stage(60) == LifeStage.LATE_CAREER
    assert get_life_stage(69) == LifeStage.LATE_CAREER
    assert get_life_stage(70) == LifeStage.RETIRED
    assert get_life_stage(95) == LifeStage.RETIRED


def test_gompertz_makeham_hazard_increases_with_age():
    hazard_20 = calculate_gompertz_makeham_daily_hazard(20, health=1.0)
    hazard_50 = calculate_gompertz_makeham_daily_hazard(50, health=1.0)
    hazard_80 = calculate_gompertz_makeham_daily_hazard(80, health=1.0)

    assert 0.0 < hazard_20 < hazard_50 < hazard_80 < 1.0


def test_gompertz_makeham_health_penalty():
    hazard_healthy = calculate_gompertz_makeham_daily_hazard(70, health=1.0)
    hazard_impaired = calculate_gompertz_makeham_daily_hazard(70, health=0.05)

    assert hazard_impaired > hazard_healthy


def test_evaluate_mortality_statistical():
    rng = random.Random(42)
    # Very young healthy agents should rarely die
    deaths_young = sum(evaluate_daily_mortality(25, 1.0, rng) for _ in range(1000))
    assert deaths_young <= 5

    # Very old and sick agents should have noticeably higher mortality
    rng2 = random.Random(42)
    deaths_old_sick = sum(evaluate_daily_mortality(95, 0.05, rng2) for _ in range(1000))
    assert deaths_old_sick > deaths_young
