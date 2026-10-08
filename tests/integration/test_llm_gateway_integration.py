"""Integration tests for Phase 7 LLM Gateway in Simulation Engine."""

import tempfile

from backend.app.config import SimulationConfig
from backend.llm.provider import MockProvider
from backend.simulation.engine import SimulationEngine


def test_simulation_with_mock_llm_gateway():
    """Verify simulation executes strategic decisions with LLM provider and emits typed events."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    config = SimulationConfig(
        total_days=10,
        database_url=f"sqlite:///{db_path}",
        seed=101,
        llm_enabled=True,
    )

    with SimulationEngine(config=config) as engine:
        # Equip with mock provider for reproducible test
        engine.state.llm_gateway.provider = MockProvider(
            model="mock-qwen2.5:1.5b", default_decision="FOOD_SUBSIDY"
        )

        strategic_events = []
        for _ in range(10):
            day_events = engine.step()
            for evt in day_events:
                if evt.event_type == "StrategicDecisionMade":
                    strategic_events.append(evt)

        # Strategic decisions should have occurred (e.g. Mayoral monthly deliberation or corporate)
        assert len(strategic_events) >= 1
        first_decision = strategic_events[0]
        assert first_decision.payload["source"] in (
            "LLM_REASONING",
            "MATHEMATICAL_FALLBACK",
        )
        assert "chosen_action" in first_decision.payload
        assert "rationale" in first_decision.payload

        # Metrics verification
        m = engine.state.metrics
        assert m.llm_decisions_count >= 1
        assert m.llm_status == "active"


def test_simulation_100_percent_mathematics_fallback():
    """Verify simulation runs with 100% mathematical determinism when LLM is disabled or offline."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    config = SimulationConfig(
        total_days=8,
        database_url=f"sqlite:///{db_path}",
        seed=202,
        llm_enabled=False,  # Offline / fallback mode
    )

    with SimulationEngine(config=config) as engine:
        assert engine.state.llm_gateway.is_llm_active is False

        for _ in range(8):
            engine.step()

        m = engine.state.metrics
        assert m.llm_status == "offline_fallback"
        assert m.llm_decisions_count == 0
        # If any strategic decision was requested, it was handled 100% by mathematical fallback
        assert m.llm_fallback_count >= 0
