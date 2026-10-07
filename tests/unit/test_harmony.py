"""Unit tests for Phase 6 Society Harmony Index, Distrust & Feedback."""

from backend.information.harmony import SocietyHarmonyTracker
from backend.information.rumors import Rumor
from backend.simulation.districts import initialize_districts
from backend.simulation.state import WorldState
from backend.society.relationships import RelationshipGraph, RelationType


def test_harmony_tracker_baseline_and_peace():
    """Verify high civic satisfaction and peace yield high harmony."""
    tracker = SocietyHarmonyTracker(harmony_index=0.75)
    ws = WorldState(run_id="test_run", seed=42, districts=initialize_districts())
    relationships = RelationshipGraph()
    relationships.add_edge("a1", "a2", RelationType.FRIEND, trust=0.70)

    # Positive civic conditions
    ws.metrics.approval_rating = 85.0
    ws.metrics.city_unrest = 0.05
    ws.metrics.rioting_districts_count = 0
    ws.government.corruption_index = 0.01

    h, distrust, penalty = tracker.update_harmony(
        world_state=ws,
        active_rumors={},
        relationships=relationships,
    )

    assert h >= 0.70
    assert distrust <= 0.30
    assert penalty == 0.0
    # Social trust should slowly heal or remain high
    assert relationships.average_trust >= 0.70


def test_harmony_tracker_disharmony_feedback():
    """Verify toxic conditions cause trust erosion and generate unrest penalty."""
    tracker = SocietyHarmonyTracker(harmony_index=0.45)
    ws = WorldState(run_id="test_run", seed=42, districts=initialize_districts())
    relationships = RelationshipGraph()
    relationships.add_edge("a1", "a2", RelationType.FRIEND, trust=0.50)

    # Toxic rumors
    rumors = {
        "r1": Rumor(
            rumor_id="r1",
            topic="COLLAPSE",
            headline="Imminent Collapse",
            intensity=0.9,
            veracity=0.1,  # Fabricated toxic panic
            origin_tick=1,
        )
    }

    # Severe civic distress
    ws.metrics.approval_rating = 15.0
    ws.metrics.city_unrest = 0.70
    ws.metrics.rioting_districts_count = 3
    ws.government.corruption_index = 0.35

    h, distrust, penalty = tracker.update_harmony(
        world_state=ws,
        active_rumors=rumors,
        relationships=relationships,
    )

    assert h < 0.50
    assert distrust > 0.50
    assert penalty > 0.0  # Positive unrest penalty fueling riots
    # Social trust was eroded
    assert relationships.average_trust < 0.50

    d = tracker.to_dict()
    assert d["harmony_index"] == h
    assert d["interpersonal_distrust"] == distrust
    assert d["disinformation_index"] > 0.0
