"""Unit tests for StrategicLLMGateway Module."""

import random

from backend.agents.agent import Agent
from backend.agents.personality import generate_personality
from backend.agents.roles import RoleType
from backend.companies.company import Company
from backend.economy.goods import CommodityType
from backend.llm.gateway import StrategicLLMGateway
from backend.llm.provider import MockProvider, OllamaProvider
from backend.simulation.districts import initialize_districts
from backend.simulation.state import WorldState


def test_gateway_with_mock_provider():
    """Verify gateway uses LLM provider when active and healthy."""
    mock = MockProvider(default_decision="FOOD_SUBSIDY", confidence=0.92)
    gateway = StrategicLLMGateway(provider=mock, enabled=True)

    assert gateway.is_llm_active is True

    ws = WorldState(run_id="test", seed=1, districts=initialize_districts())
    ws.government.treasury = 5000.0

    rng = random.Random(42)
    mayor = Agent(
        id="a_mayor",
        age_days=15000,
        sex="M",
        role=RoleType.MAYOR,
        personality=generate_personality(rng),
        district_id="dist_central",
        cash=5000.0,
    )

    res = gateway.decide_mayoral_crisis(mayor, ws)
    assert res.source == "LLM_REASONING"
    assert res.chosen_action == "FOOD_SUBSIDY"
    assert res.confidence == 0.92
    assert res.model_used == "mock-qwen2.5:1.5b"
    assert gateway.llm_decisions == 1
    assert gateway.fallback_decisions == 0

    d = gateway.to_dict()
    assert d["llm_enabled"] is True
    assert d["is_active"] is True
    assert d["llm_decisions"] == 1
    assert gateway.average_latency_ms >= 0.0


def test_gateway_with_offline_provider_fallback():
    """Verify gateway seamlessly uses 100% mathematical fallback when LLM is offline."""
    offline_provider = OllamaProvider(
        base_url="http://127.0.0.1:59999", model="qwen2.5:1.5b", timeout_seconds=0.2
    )
    gateway = StrategicLLMGateway(provider=offline_provider, enabled=True)

    assert gateway.is_llm_active is False

    ws = WorldState(run_id="test", seed=1, districts=initialize_districts())
    ws.metrics.inflation_rate = 9.0
    ws.government.treasury = 3000.0

    rng = random.Random(42)
    mayor = Agent(
        id="a_mayor",
        age_days=15000,
        sex="M",
        role=RoleType.MAYOR,
        personality=generate_personality(rng),
        district_id="dist_central",
        cash=5000.0,
    )

    res = gateway.decide_mayoral_crisis(mayor, ws)
    assert res.source == "MATHEMATICAL_FALLBACK"
    assert res.chosen_action == "FOOD_SUBSIDY"
    assert res.model_used is None
    assert gateway.fallback_decisions == 1
    assert gateway.llm_decisions == 0
    offline_provider.close()


def test_gateway_corporate_strategy():
    """Verify gateway handles corporate strategy decisions."""
    mock = MockProvider(default_decision="CONSERVE_CAPITAL")
    gateway = StrategicLLMGateway(provider=mock, enabled=True)

    ws = WorldState(run_id="test", seed=1, districts=initialize_districts())
    rng = random.Random(42)
    ceo = Agent(
        id="a_ceo",
        age_days=14000,
        sex="F",
        role=RoleType.BUSINESS_OWNER,
        personality=generate_personality(rng),
        district_id="dist_industrial",
        cash=8000.0,
    )
    comp = Company(
        id="comp_1",
        name="Apex Agro",
        district_id="dist_industrial",
        commodity_type=CommodityType.FOOD,
        capital=5000.0,
        cash=1000.0,
        target_wage=25.0,
        inventory=15.0,
        ticker="APEX",
    )

    res = gateway.decide_corporate_strategy(ceo, comp, ws)
    assert res.source == "LLM_REASONING"
    assert res.chosen_action == "CONSERVE_CAPITAL"
    assert res.role == "BUSINESS_OWNER"
