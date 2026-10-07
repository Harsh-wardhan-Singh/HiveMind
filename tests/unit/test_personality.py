"""Unit tests for Personality generation and Big-Five model."""

import random

from backend.agents.personality import Personality, generate_personality


def test_personality_determinism():
    rng1 = random.Random(42)
    rng2 = random.Random(42)

    p1 = generate_personality(rng1)
    p2 = generate_personality(rng2)

    assert p1.openness == p2.openness
    assert p1.conscientiousness == p2.conscientiousness
    assert p1.extraversion == p2.extraversion
    assert p1.agreeableness == p2.agreeableness
    assert p1.neuroticism == p2.neuroticism
    assert p1.risk_tolerance == p2.risk_tolerance
    assert p1.social_trust == p2.social_trust
    assert p1.ambition == p2.ambition


def test_personality_bounds():
    rng = random.Random(999)
    for _ in range(100):
        p = generate_personality(rng)
        for val in [
            p.openness,
            p.conscientiousness,
            p.extraversion,
            p.agreeableness,
            p.neuroticism,
            p.risk_tolerance,
            p.social_trust,
            p.ambition,
        ]:
            assert 0.0 <= val <= 1.0, f"Personality trait out of bounds: {val}"


def test_personality_to_dict():
    p = Personality(
        openness=0.5,
        conscientiousness=0.6,
        extraversion=0.7,
        agreeableness=0.8,
        neuroticism=0.3,
        risk_tolerance=0.4,
        social_trust=0.55,
        ambition=0.65,
    )
    d = p.to_dict()
    assert len(d) == 8
    assert d["openness"] == 0.5
    assert d["ambition"] == 0.65
