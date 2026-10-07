"""Unit tests for Laspeyres CPI and Inflation calculations."""

from backend.economy.inflation import InflationTracker


def test_initial_cpi_is_100():
    tracker = InflationTracker()
    assert tracker.current_cpi == 100.0


def test_cpi_increases_with_price_hike():
    tracker = InflationTracker()
    base_prices = tracker.base_prices.copy()

    # Double all commodity prices
    inflated_prices = {c: p * 2.0 for c, p in base_prices.items()}
    cpi = tracker.update(inflated_prices)

    assert cpi == 200.0
    assert tracker.current_inflation_rate == 100.0


def test_cpi_decreases_with_deflation():
    tracker = InflationTracker()
    base_prices = tracker.base_prices.copy()

    # Half all prices
    deflated_prices = {c: p * 0.5 for c, p in base_prices.items()}
    cpi = tracker.update(deflated_prices)

    assert cpi == 50.0
    assert tracker.current_inflation_rate == -50.0
