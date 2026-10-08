"""Unit tests for Phase 6 Media Outlets & News Broadcasts."""

import random

from backend.information.media import MediaEngine, MediaOutlet, NewsArticle
from backend.simulation.districts import initialize_districts
from backend.simulation.state import WorldState


def test_media_models_serialization():
    """Verify NewsArticle and MediaOutlet models serialize to dictionary correctly."""
    outlet = MediaOutlet(
        outlet_id="press_test",
        name="Test Times",
        bias_factor=0.25,
        credibility=0.85,
        sensationalism=0.10,
    )
    d_out = outlet.to_dict()
    assert d_out["outlet_id"] == "press_test"
    assert d_out["credibility"] == 0.85

    article = NewsArticle(
        article_id="art_001",
        headline="Major Economic Growth",
        topic="ECONOMY",
        summary="City records rising production.",
        sentiment=0.75,
        credibility=0.85,
        publisher="Test Times",
        tick=5,
    )
    d_art = article.to_dict()
    assert d_art["article_id"] == "art_001"
    assert d_art["sentiment"] == 0.75
    assert d_art["tick"] == 5


def test_media_engine_riot_news():
    """Verify MediaEngine generates sensationalist alert during riots."""
    engine = MediaEngine()
    ws = WorldState(run_id="test_run", seed=42, districts=initialize_districts())
    ws.clock.current_tick = 10
    ws.metrics.rioting_districts_count = 2

    rng = random.Random(42)
    articles = engine.generate_daily_news(ws, rng)

    assert len(articles) >= 1
    riot_art = articles[0]
    assert riot_art.topic == "RIOT_ALERT"
    assert "Civil Disturbance Erupts" in riot_art.headline
    assert riot_art.sentiment < 0.0
    assert len(engine.articles_archive) == len(articles)


def test_media_engine_inflation_news():
    """Verify MediaEngine generates cost-of-living alert during inflation spikes."""
    engine = MediaEngine()
    ws = WorldState(run_id="test_run", seed=42, districts=initialize_districts())
    ws.clock.current_tick = 5
    ws.metrics.rioting_districts_count = 0
    ws.metrics.inflation_rate = 8.5
    ws.metrics.cpi = 122.0

    rng = random.Random(42)
    articles = engine.generate_daily_news(ws, rng)

    assert len(articles) >= 1
    infl_art = articles[0]
    assert infl_art.topic == "INFLATION_SURGE"
    assert "Cost of Living Alert" in infl_art.headline


def test_media_engine_archive_cap():
    """Verify rolling archive caps at 60 articles."""
    engine = MediaEngine()
    ws = WorldState(run_id="test_run", seed=42, districts=initialize_districts())
    rng = random.Random(42)

    for tick in range(1, 100):
        ws.clock.current_tick = tick
        ws.metrics.rioting_districts_count = 1
        engine.generate_daily_news(ws, rng)

    assert len(engine.articles_archive) <= 60
    assert engine.to_dict()["archive_count"] <= 60
