"""Unit tests for SimulationClock."""

import pytest

from backend.simulation.clock import SimulationClock


def test_clock_initial_state():
    clock = SimulationClock()
    assert clock.current_tick == 0
    assert clock.current_day == 0
    assert clock.current_year == 0
    assert clock.day_of_year == 1
    assert clock.format_date() == "Year 1, Day 1"


def test_clock_advance():
    clock = SimulationClock()
    tick = clock.advance(1)
    assert tick == 1
    assert clock.current_day == 1
    assert clock.day_of_year == 2

    clock.advance(10)
    assert clock.current_tick == 11
    assert clock.day_of_year == 12


def test_clock_year_progression():
    clock = SimulationClock()
    clock.advance(366)
    assert clock.current_year == 1
    assert clock.format_date() == "Year 2, Day 2"


def test_clock_invalid_advance():
    clock = SimulationClock()
    with pytest.raises(ValueError):
        clock.advance(0)
    with pytest.raises(ValueError):
        clock.advance(-5)
