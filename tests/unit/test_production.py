"""Unit tests for Cobb-Douglas Production."""

from backend.companies.company import Company
from backend.companies.production import calculate_cobb_douglas_output
from backend.economy.goods import CommodityType


def test_cobb_douglas_zero_inputs():
    assert calculate_cobb_douglas_output(1.0, 0.0, [0.5, 0.8]) == 0.0
    assert calculate_cobb_douglas_output(1.0, 1000.0, []) == 0.0
    assert calculate_cobb_douglas_output(0.0, 1000.0, [0.5]) == 0.0


def test_cobb_douglas_positive_output():
    # Y = A * K^0.3 * L^0.7
    # K = 1000, L = 1.0 (single worker skill 1.0)
    # 1000^0.3 = 7.943, 1.0^0.7 = 1.0 -> output ~ 7.943
    output = calculate_cobb_douglas_output(1.0, 1000.0, [1.0])
    assert 7.9 < output < 8.0


def test_company_production_increases_inventory():
    comp = Company(
        id="comp_test",
        name="Test Factory",
        district_id="dist_industrial",
        commodity_type=CommodityType.CONSUMER_GOODS,
        capital=5000.0,
        inventory=100.0,
    )
    initial_inv = comp.inventory
    output = comp.produce([0.8, 0.6])
    assert output > 0.0
    assert comp.inventory == initial_inv + output

