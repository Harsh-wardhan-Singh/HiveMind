"""HIVEMIND Commodity & Goods Catalog Module."""

from dataclasses import dataclass
from enum import Enum


class CommodityType(str, Enum):
    FOOD = "FOOD"
    HOUSING = "HOUSING"
    HEALTHCARE = "HEALTHCARE"
    CONSUMER_GOODS = "CONSUMER_GOODS"


@dataclass(frozen=True)
class CommodityDefinition:
    commodity_type: CommodityType
    name: str
    base_price: float
    min_price: float
    max_price: float
    daily_subsistence_per_person: float  # Units required daily per living agent
    perishability_rate: float  # Fraction of inventory lost per day (decay)


COMMODITY_DEFINITIONS: dict[CommodityType, CommodityDefinition] = {
    CommodityType.FOOD: CommodityDefinition(
        commodity_type=CommodityType.FOOD,
        name="Food & Sustenance",
        base_price=10.0,
        min_price=7.0,
        max_price=30.0,
        daily_subsistence_per_person=1.0,
        perishability_rate=0.01,  # 1% daily spoilage
    ),
    CommodityType.HOUSING: CommodityDefinition(
        commodity_type=CommodityType.HOUSING,
        name="Housing & Shelter",
        base_price=25.0,  # Base daily rental equivalent
        min_price=15.0,
        max_price=50.0,
        daily_subsistence_per_person=1.0,
        perishability_rate=0.0005,  # Slow physical wear
    ),
    CommodityType.HEALTHCARE: CommodityDefinition(
        commodity_type=CommodityType.HEALTHCARE,
        name="Healthcare & Medical Care",
        base_price=30.0,
        min_price=15.0,
        max_price=60.0,
        daily_subsistence_per_person=0.1,  # Purchased when sick/maintenance
        perishability_rate=0.002,
    ),
    CommodityType.CONSUMER_GOODS: CommodityDefinition(
        commodity_type=CommodityType.CONSUMER_GOODS,
        name="Consumer Goods & Appliances",
        base_price=15.0,
        min_price=8.0,
        max_price=35.0,
        daily_subsistence_per_person=0.2,
        perishability_rate=0.001,
    ),
}


def get_commodity_definition(c_type: CommodityType) -> CommodityDefinition:
    return COMMODITY_DEFINITIONS[c_type]
