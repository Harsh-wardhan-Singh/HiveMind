"""Unit tests for Citizen Favorability & Approval Rating Dynamics."""

from backend.agents.agent import Agent
from backend.agents.personality import Personality
from backend.politics.favorability import (
    calculate_agent_favorability,
    update_all_favorability,
)
from backend.simulation.districts import District


def test_favorability_factors_up_and_down():
    district_safe = District(
        id="d1",
        name="Sunnyvale",
        land_price=200.0,
        rent=20.0,
        safety_score=0.90,
        transport_connectivity=0.9,
        housing_units=100,
    )
    district_unsafe = District(
        id="d2",
        name="Rust Belt",
        land_price=50.0,
        rent=5.0,
        safety_score=0.15,
        transport_connectivity=0.3,
        housing_units=50,
    )

    # Thriving citizen in safe district with public assistance
    thriving_agent = Agent(
        id="thrive_1",
        age_days=12000,
        district_id="d1",
        cash=5000.0,
        health=0.98,
        employer_id="comp_1",
        public_help_received=40.0,
        favorability=0.5,
    )

    # Suffering citizen in dangerous district with hunger and corruption
    suffering_agent = Agent(
        id="suffer_1",
        age_days=12000,
        district_id="d2",
        cash=10.0,
        health=0.20,  # Severe starvation
        employer_id=None,
        favorability=0.5,
    )

    fav_thriving = calculate_agent_favorability(
        agent=thriving_agent,
        district=district_safe,
        inflation_rate=1.0,
        corruption_index=0.02,
    )

    fav_suffering = calculate_agent_favorability(
        agent=suffering_agent,
        district=district_unsafe,
        inflation_rate=12.0,  # High inflation
        corruption_index=0.25,  # Rampant corruption
        has_recent_scandal=True,
    )

    assert fav_thriving > fav_suffering
    assert fav_thriving >= 0.55
    assert fav_suffering < 0.45


def test_corruption_penalty_amplified_by_conscientiousness():
    district = District(
        id="d1",
        name="Metro",
        land_price=100.0,
        rent=10.0,
        safety_score=0.7,
        transport_connectivity=0.7,
        housing_units=100,
    )

    honest_agent = Agent(
        id="a_honest",
        age_days=10000,
        district_id="d1",
        cash=1000.0,
        health=0.9,
        personality=Personality(
            openness=0.5,
            conscientiousness=0.95,  # High integrity
            extraversion=0.5,
            agreeableness=0.5,
            neuroticism=0.5,
            risk_tolerance=0.5,
            social_trust=0.90,  # High trust feels betrayed
            ambition=0.5,
        ),
        favorability=0.5,
    )

    apathetic_agent = Agent(
        id="a_apathetic",
        age_days=10000,
        district_id="d1",
        cash=1000.0,
        health=0.9,
        personality=Personality(
            openness=0.5,
            conscientiousness=0.1,  # Low conscientiousness
            extraversion=0.5,
            agreeableness=0.5,
            neuroticism=0.5,
            risk_tolerance=0.5,
            social_trust=0.1,  # Low trust
            ambition=0.5,
        ),
        favorability=0.5,
    )

    fav_honest = calculate_agent_favorability(
        agent=honest_agent,
        district=district,
        inflation_rate=2.0,
        corruption_index=0.20,
    )

    fav_apathetic = calculate_agent_favorability(
        agent=apathetic_agent,
        district=district,
        inflation_rate=2.0,
        corruption_index=0.20,
    )

    assert fav_honest < fav_apathetic


def test_update_all_favorability_and_approval_rating():
    agents = {
        "a1": Agent(
            id="a1",
            age_days=10000,
            district_id="d1",
            cash=3000.0,
            health=0.95,
            favorability=0.7,
        ),
        "a2": Agent(
            id="a2",
            age_days=10000,
            district_id="d1",
            cash=2000.0,
            health=0.90,
            favorability=0.6,
        ),
        "a3": Agent(
            id="a3",
            age_days=10000,
            district_id="d1",
            cash=50.0,
            health=0.30,
            favorability=0.2,
        ),
    }
    districts = {
        "d1": District(
            id="d1",
            name="City",
            land_price=100.0,
            rent=10.0,
            safety_score=0.8,
            transport_connectivity=0.8,
            housing_units=100,
        )
    }

    avg_fav, approval_pct = update_all_favorability(
        agents=agents,
        districts=districts,
        inflation_rate=1.5,
        corruption_index=0.03,
    )

    assert 0.0 <= avg_fav <= 1.0
    assert 0.0 <= approval_pct <= 100.0
    assert approval_pct > 50.0  # At least 2 out of 3 approve
