"""Integration tests for Phase 6 Information Ecology, Media, Rumors & Harmony System."""

import tempfile

from backend.app.config import SimulationConfig
from backend.simulation.engine import SimulationEngine


def test_information_system_multi_day_lifecycle():
    """Verify daily news publication, rumor diffusion, harmony tracking, and bounded observations."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    db_url = f"sqlite:///{db_path}"
    config = SimulationConfig(
        total_days=10,
        database_url=db_url,
        seed=42,
    )

    with SimulationEngine(config=config) as engine:
        # Initial state checks
        assert engine.state.harmony_tracker.harmony_index > 0.0
        assert engine.state.metrics.society_harmony_index > 0.0

        events_seen = set()
        for _ in range(10):
            day_events = engine.step()
            for evt in day_events:
                events_seen.add(evt.event_type)

        # Check required Phase 6 event emissions
        assert "NewsPublished" in events_seen
        assert "HarmonyShifted" in events_seen

        # Verify engine observation packet generation
        sample_agent_id = next(iter(engine.state.agents.keys()))
        obs = engine.get_agent_observation(sample_agent_id)
        assert obs is not None
        assert obs.agent_id == sample_agent_id
        assert obs.personal_ledger["cash"] > 0
        assert len(obs.known_districts) > 0

        # Verify metrics updated
        metrics = engine.state.metrics
        assert 0.0 <= metrics.society_harmony_index <= 1.0
        assert 0.0 <= metrics.interpersonal_distrust <= 1.0
        assert metrics.media_articles_count >= 1


def test_information_system_determinism():
    """Verify bit-for-bit identical information, rumors, news, and harmony between two identical seeds."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp1:
        db1 = tmp1.name
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp2:
        db2 = tmp2.name

    conf1 = SimulationConfig(
        total_days=8,
        database_url=f"sqlite:///{db1}",
        seed=9999,
    )
    conf2 = SimulationConfig(
        total_days=8,
        database_url=f"sqlite:///{db2}",
        seed=9999,
    )

    with SimulationEngine(config=conf1) as eng1, SimulationEngine(config=conf2) as eng2:
        for _ in range(8):
            eng1.step()
            eng2.step()

        m1 = eng1.state.metrics
        m2 = eng2.state.metrics

        assert m1.society_harmony_index == m2.society_harmony_index
        assert m1.interpersonal_distrust == m2.interpersonal_distrust
        assert m1.active_rumors_count == m2.active_rumors_count
        assert m1.media_articles_count == m2.media_articles_count
        assert m1.mean_social_trust == m2.mean_social_trust

        # Verify observation packet bit-for-bit equality
        first_agent = next(iter(eng1.state.agents.keys()))
        obs1 = eng1.get_agent_observation(first_agent)
        obs2 = eng2.get_agent_observation(first_agent)
        assert obs1 is not None and obs2 is not None
        assert obs1.to_dict() == obs2.to_dict()
