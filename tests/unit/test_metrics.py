"""Unit tests for CityMetrics calculations."""

from backend.simulation.agent import Agent
from backend.simulation.metrics import CityMetrics, calculate_metrics


def test_calculate_metrics_empty():
    metrics = calculate_metrics({})
    assert isinstance(metrics, CityMetrics)
    assert metrics.total_population == 0
    assert metrics.alive_population == 0


def test_calculate_metrics_with_agents():
    agents = {
        "a1": Agent(
            id="a1",
            age_days=365 * 25,
            district_id="dist_central",
            cash=2000.0,
            health=0.9,
            alive=True,
        ),
        "a2": Agent(
            id="a2",
            age_days=365 * 35,
            district_id="dist_north",
            cash=4000.0,
            health=0.7,
            alive=True,
        ),
        "a3": Agent(
            id="a3",
            age_days=365 * 50,
            district_id="dist_south",
            cash=1000.0,
            health=0.0,
            alive=False,
        ),
    }

    metrics = calculate_metrics(agents)
    assert metrics.total_population == 3
    assert metrics.alive_population == 2
    assert metrics.total_cash == 6000.0
    assert metrics.average_cash == 3000.0
    assert metrics.average_health == 0.8
    assert metrics.average_age_years == 29.0


def test_metrics_serialization():
    metrics = CityMetrics(
        total_population=100,
        alive_population=98,
        average_health=0.91234,
        total_cash=50000.55,
    )
    data = metrics.to_dict()
    assert data["total_population"] == 100
    assert data["average_health"] == 0.9123
