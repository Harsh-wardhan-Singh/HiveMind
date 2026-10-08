"""Unit tests for Phase 7 Action Validator Module."""

from backend.llm.validator import (
    validate_corporate_proposal,
    validate_mayoral_proposal,
)
from backend.simulation.districts import initialize_districts
from backend.simulation.state import WorldState


class DummyCompany:
    def __init__(self, cash: float = 1000.0):
        self.cash = cash


def test_validate_mayoral_proposal_success():
    """Verify valid policy with sufficient treasury is approved."""
    ws = WorldState(run_id="test", seed=1, districts=initialize_districts())
    ws.government.treasury = 5000.0

    is_valid, action, _reason = validate_mayoral_proposal("FOOD_SUBSIDY", ws)
    assert is_valid is True
    assert action == "FOOD_SUBSIDY"


def test_validate_mayoral_proposal_budget_downscale():
    """Verify unaffordable policy is downscaled to Austerity or rejected."""
    ws = WorldState(run_id="test", seed=1, districts=initialize_districts())
    ws.government.treasury = 500.0  # Cannot afford Public Works (needs 4000)

    is_valid, action, reason = validate_mayoral_proposal("PUBLIC_WORKS", ws)
    assert is_valid is False
    assert action == "AUSTERITY"
    assert "Insufficient treasury" in reason


def test_validate_mayoral_proposal_invalid_action():
    """Verify illegal/hallucinated action is rejected."""
    ws = WorldState(run_id="test", seed=1, districts=initialize_districts())

    is_valid, action, _reason = validate_mayoral_proposal("BUILD_DEATH_STAR", ws)
    assert is_valid is False
    assert action == "NO_ACTION"


def test_validate_corporate_proposal():
    """Verify corporate action validation and liquidity constraint."""
    comp_rich = DummyCompany(cash=2000.0)
    is_valid, action, _reason = validate_corporate_proposal(
        "EXPAND_PRODUCTION", comp_rich
    )
    assert is_valid is True
    assert action == "EXPAND_PRODUCTION"

    comp_poor = DummyCompany(cash=100.0)
    is_valid, action, _reason = validate_corporate_proposal(
        "EXPAND_PRODUCTION", comp_poor
    )
    assert is_valid is False
    assert action == "CONSERVE_CAPITAL"
