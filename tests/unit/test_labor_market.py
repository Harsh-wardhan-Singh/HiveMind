"""Unit tests for Labor Market matching and payroll."""

import random

from backend.agents.agent import Agent
from backend.agents.roles import RoleType
from backend.companies.company import Company
from backend.economy.goods import CommodityType
from backend.labor.market import (
    calculate_reservation_wage,
    match_labor_market,
    process_daily_payroll,
)


def test_reservation_wage():
    agent = Agent(
        id="a1",
        age_days=365 * 30,
        district_id="dist_central",
        cash=1000.0,
        role=RoleType.ENGINEER,
    )
    res_wage = calculate_reservation_wage(agent)
    assert res_wage >= 15.0
    assert res_wage >= 200.0  # High engineer salary baseline


def test_labor_market_matching():
    rng = random.Random(42)
    agents = {
        "a1": Agent(
            id="a1",
            age_days=365 * 25,
            district_id="dist_north",
            cash=500.0,
            role=RoleType.MANUAL_WORKER,
        ),
        "a2": Agent(
            id="a2",
            age_days=365 * 28,
            district_id="dist_north",
            cash=800.0,
            role=RoleType.SKILLED_WORKER,
        ),
    }

    companies = {
        "c1": Company(
            id="c1",
            name="Workshop",
            district_id="dist_north",
            commodity_type=CommodityType.CONSUMER_GOODS,
            capital=5000.0,
            target_wage=150.0,
        )
    }

    hires = match_labor_market(agents, companies, rng)
    assert len(hires) > 0
    assert len(companies["c1"].employee_ids) > 0


def test_payroll_disbursement_transfers_cash():
    agents = {
        "a1": Agent(
            id="a1",
            age_days=365 * 30,
            district_id="dist_central",
            cash=100.0,
            employer_id="c1",
        )
    }

    comp = Company(
        id="c1",
        name="Tech",
        district_id="dist_central",
        commodity_type=CommodityType.CONSUMER_GOODS,
        cash=10000.0,
        target_wage=200.0,
    )
    comp.add_employee("a1")
    companies = {"c1": comp}

    payroll = process_daily_payroll(agents, companies)
    assert payroll["c1"] == 200.0
    assert agents["a1"].cash == 300.0
    assert comp.cash == 9800.0
