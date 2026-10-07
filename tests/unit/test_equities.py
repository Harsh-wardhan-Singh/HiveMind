"""Unit tests for Corporate Equities, Share Registry, and Dividends."""

from backend.agents.agent import Agent
from backend.agents.roles import RoleType
from backend.companies.company import Company
from backend.economy.goods import CommodityType
from backend.markets.equities import ShareRegistry


def test_share_issuance_and_registry():
    registry = ShareRegistry()
    equity = registry.issue_shares(
        company_id="comp_1",
        ticker="AGRI",
        total_shares=10_000,
        initial_holders={"agent_1": 2_000, "comp_1": 8_000},
    )

    assert equity.ticker == "AGRI"
    assert equity.total_shares == 10_000
    assert equity.get_holder_shares("agent_1") == 2_000
    assert equity.get_holder_shares("comp_1") == 8_000
    assert registry.get_company_ticker("comp_1") == "AGRI"


def test_share_transfer():
    registry = ShareRegistry()
    registry.issue_shares(
        company_id="comp_1",
        ticker="AGRI",
        total_shares=10_000,
        initial_holders={"agent_1": 2_000},
    )

    # Valid transfer
    success = registry.transfer_shares("AGRI", "agent_1", "agent_2", 500)
    assert success is True
    assert registry.get_equity("AGRI").get_holder_shares("agent_1") == 1_500
    assert registry.get_equity("AGRI").get_holder_shares("agent_2") == 500

    # Overdraft transfer (insufficient shares)
    fail = registry.transfer_shares("AGRI", "agent_1", "agent_2", 2000)
    assert fail is False
    assert registry.get_equity("AGRI").get_holder_shares("agent_1") == 1_500


def test_dividend_distribution_profitable_company():
    registry = ShareRegistry()
    registry.issue_shares(
        company_id="comp_1",
        ticker="AGRI",
        total_shares=10_000,
        initial_holders={"agent_1": 4_000, "agent_2": 6_000},
    )

    company = Company(
        id="comp_1",
        name="Agri Corp",
        district_id="dist_north",
        commodity_type=CommodityType.FOOD,
        cash=10_000.0,
        daily_profit=1_000.0,
        solvency=True,
    )

    agent1 = Agent(
        id="agent_1",
        age_days=10000,
        district_id="dist_north",
        cash=500.0,
        role=RoleType.INVESTOR,
    )
    agent2 = Agent(
        id="agent_2",
        age_days=10000,
        district_id="dist_north",
        cash=800.0,
        role=RoleType.BUSINESS_OWNER,
    )
    agents = {"agent_1": agent1, "agent_2": agent2}

    # Payout ratio 35%: 1000 * 0.35 = 350.0 total dividend
    total_div = registry.declare_and_distribute_dividends(
        company=company,
        agents=agents,
        payout_ratio=0.35,
    )

    assert total_div == 350.0
    assert company.cash == 10_000.0 - 350.0
    # agent1 has 40% of shares -> 40% of 350 = 140.0
    assert agent1.cash == 500.0 + 140.0
    # agent2 has 60% of shares -> 60% of 350 = 210.0
    assert agent2.cash == 800.0 + 210.0


def test_dividend_distribution_unprofitable_company():
    registry = ShareRegistry()
    registry.issue_shares(
        company_id="comp_1",
        ticker="AGRI",
        total_shares=10_000,
        initial_holders={"agent_1": 10_000},
    )

    company = Company(
        id="comp_1",
        name="Agri Corp",
        district_id="dist_north",
        commodity_type=CommodityType.FOOD,
        cash=8_000.0,
        daily_profit=-200.0,  # Negative profit
        solvency=True,
    )

    agent1 = Agent(
        id="agent_1",
        age_days=10000,
        district_id="dist_north",
        cash=500.0,
        role=RoleType.INVESTOR,
    )
    agents = {"agent_1": agent1}

    total_div = registry.declare_and_distribute_dividends(company, agents)
    assert total_div == 0.0
    assert agent1.cash == 500.0
    assert company.cash == 8_000.0

