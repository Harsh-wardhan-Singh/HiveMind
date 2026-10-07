"""HIVEMIND Laspeyres Consumer Price Index (CPI) & Inflation Tracker."""

from dataclasses import dataclass, field

from backend.economy.goods import COMMODITY_DEFINITIONS, CommodityType


@dataclass
class InflationTracker:
    base_prices: dict[CommodityType, float] = field(default_factory=dict)
    basket_weights: dict[CommodityType, float] = field(default_factory=dict)
    cpi_history: list[float] = field(default_factory=list)
    current_cpi: float = 100.0
    current_inflation_rate: float = 0.0

    def __post_init__(self):
        if not self.base_prices:
            self.base_prices = {
                c_type: c_def.base_price
                for c_type, c_def in COMMODITY_DEFINITIONS.items()
            }
        if not self.basket_weights:
            self.basket_weights = {
                c_type: c_def.daily_subsistence_per_person
                for c_type, c_def in COMMODITY_DEFINITIONS.items()
            }

    def update(self, current_prices: dict[CommodityType, float]) -> float:
        """
        Calculate current Laspeyres CPI:
        CPI = (sum(P_{c, t} * Q_{c, 0}) / sum(P_{c, 0} * Q_{c, 0})) * 100
        """
        base_basket_cost = sum(
            self.base_prices[c] * self.basket_weights[c] for c in CommodityType
        )
        current_basket_cost = sum(
            current_prices.get(c, self.base_prices[c]) * self.basket_weights[c]
            for c in CommodityType
        )

        if base_basket_cost <= 0.0:
            cpi = 100.0
        else:
            cpi = (current_basket_cost / base_basket_cost) * 100.0

        self.current_cpi = round(cpi, 2)
        self.cpi_history.append(self.current_cpi)

        # Rolling 30-day inflation rate
        if len(self.cpi_history) > 30:
            cpi_30_days_ago = self.cpi_history[-31]
            if cpi_30_days_ago > 0:
                self.current_inflation_rate = round(
                    ((self.current_cpi - cpi_30_days_ago) / cpi_30_days_ago) * 100.0,
                    2,
                )
        else:
            self.current_inflation_rate = round(self.current_cpi - 100.0, 2)

        return self.current_cpi

    def to_dict(self) -> dict:
        return {
            "current_cpi": self.current_cpi,
            "current_inflation_rate": self.current_inflation_rate,
            "sample_count": len(self.cpi_history),
        }
