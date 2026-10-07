"""HIVEMIND Discrete Simulation Clock."""

import math
from dataclasses import dataclass


@dataclass
class SimulationClock:
    current_tick: int = 0  # 1 tick = 1 day

    def advance(self, days: int = 1) -> int:
        """Advance the clock by a number of days and return the new tick."""
        if days < 1:
            raise ValueError("Advance days must be >= 1")
        self.current_tick += days
        return self.current_tick

    @property
    def current_day(self) -> int:
        return self.current_tick

    @property
    def current_year(self) -> int:
        """Calculate whole completed years using 365.25 days/year."""
        return math.floor(self.current_tick / 365.25)

    @property
    def day_of_year(self) -> int:
        """Day of current year (1-365)."""
        return (self.current_tick % 365) + 1

    def format_date(self) -> str:
        """Format as Year Y, Day D."""
        return f"Year {self.current_year + 1}, Day {self.day_of_year}"

