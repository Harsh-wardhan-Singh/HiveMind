"""Unit tests for Phase 7 Deterministic Mathematical Fallback Engine."""

from backend.llm.fallback import (
    fallback_corporate_decision,
    fallback_mayoral_decision,
)
from backend.simulation.districts import initialize_districts
from backend.simulation.state import WorldState


class MockCorp:
    def __init__(self, cash: float, inventory: float, profit: float):
        self.cash = cash
        self.inventory = inventory
        self.daily_profit = profit


def test_fallback_mayoral_decision_crises():
    """Verify deterministic policy selection under varying crises."""
    ws = WorldState(run_id="test", seed=1, districts=initialize_districts())

    # Case 1: Riot crisis
    ws.metrics.rioting_districts_count = 1
    ws.government.treasury = 5000.0
    action, rationale = fallback_mayoral_decision(ws)
    assert action == "PUBLIC_WORKS"
    assert "High unrest and civil riots" in rationale

    # Case 2: Inflation spike
    ws.metrics.rioting_districts_count = 0
    ws.metrics.city_unrest = 0.1
    ws.metrics.inflation_rate = 9.5
    action, rationale = fallback_mayoral_decision(ws)
    assert action == "FOOD_SUBSIDY"

    # Case 3: High corruption
    ws.metrics.inflation_rate = 2.0
    ws.government.corruption_index = 0.15
    action, rationale = fallback_mayoral_decision(ws)
    assert action == "ANTI_CORRUPTION_CRACKDOWN"

    # Case 4: Normal baseline
    ws.government.corruption_index = 0.02
    action, rationale = fallback_mayoral_decision(ws)
    assert action == "NO_ACTION"


def test_fallback_corporate_decision():
    """Verify deterministic corporate strategy under liquidity/inventory distress."""
    ws = WorldState(run_id="test", seed=1, districts=initialize_districts())

    # Stress case
    corp_stressed = MockCorp(cash=300.0, inventory=50.0, profit=-25.0)
    act, wage_adj, _rat = fallback_corporate_decision(corp_stressed, ws)
    assert act == "CONSERVE_CAPITAL"
    assert wage_adj < 0.0

    # Glut case
    corp_glut = MockCorp(cash=2000.0, inventory=150.0, profit=10.0)
    act, wage_adj, _rat = fallback_corporate_decision(corp_glut, ws)
    assert act == "CUT_PRICES"

    # Expansion case
    corp_strong = MockCorp(cash=4000.0, inventory=10.0, profit=100.0)
    act, wage_adj, _rat = fallback_corporate_decision(corp_strong, ws)
    assert act == "EXPAND_PRODUCTION"
    assert wage_adj > 0.0
