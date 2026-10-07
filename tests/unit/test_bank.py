"""Unit tests for Municipal Commercial Bank and Credit Engine."""

from backend.agents.agent import Agent
from backend.agents.roles import RoleType
from backend.banking.bank import MunicipalBank
from backend.companies.company import Company
from backend.economy.goods import CommodityType


def test_bank_deposit_and_withdrawal():
    bank = MunicipalBank(cash_reserves=50_000.0)

    # Deposit
    dep_amount = bank.deposit("agent_1", 5_000.0)
    assert dep_amount == 5_000.0
    assert bank.deposits["agent_1"] == 5_000.0
    assert bank.total_deposits == 5_000.0
    assert bank.cash_reserves == 55_000.0

    # Withdrawal
    with_amount = bank.withdraw("agent_1", 2_000.0)
    assert with_amount == 2_000.0
    assert bank.deposits["agent_1"] == 3_000.0
    assert bank.cash_reserves == 53_000.0

    # Overdraft withdrawal capped
    with_excess = bank.withdraw("agent_1", 10_000.0)
    assert with_excess == 3_000.0
    assert "agent_1" not in bank.deposits
    assert bank.total_deposits == 0.0


def test_bank_loan_underwriting():
    bank = MunicipalBank(cash_reserves=50_000.0, reserve_ratio=0.10)
    bank.deposit("depositor_1", 20_000.0)

    # Eligible loan: 5000 requested, 15000 collateral (collateral > 35%)
    approved = bank.apply_for_loan(
        borrower_id="comp_1",
        requested_amount=5_000.0,
        collateral_value=15_000.0,
    )
    assert approved is True
    assert bank.loans["comp_1"] == 5_000.0
    assert bank.total_loans == 5_000.0

    # Ineligible loan: insufficient collateral (requested 10000, collateral 1000 < 35%)
    rejected_collateral = bank.apply_for_loan(
        borrower_id="agent_broke",
        requested_amount=10_000.0,
        collateral_value=1_000.0,
    )
    assert rejected_collateral is False

    # Ineligible loan: exceeds reserve constraints
    rejected_reserve = bank.apply_for_loan(
        borrower_id="comp_huge",
        requested_amount=70_000.0,
        collateral_value=100_000.0,
    )
    assert rejected_reserve is False


def test_service_daily_banking_interest_and_amortization():
    bank = MunicipalBank(
        cash_reserves=50_000.0,
        deposit_annual_rate=0.0365,  # ~0.01% daily
        loan_annual_rate=0.0730,  # ~0.02% daily
    )
    bank.deposits["agent_1"] = 10_000.0
    bank.loans["comp_1"] = 5_000.0

    agent = Agent(
        id="agent_1",
        age_days=10000,
        district_id="dist_0",
        cash=100.0,
        role=RoleType.INVESTOR,
    )
    comp = Company(
        id="comp_1",
        name="Factory",
        district_id="dist_industrial",
        commodity_type=CommodityType.CONSUMER_GOODS,
        cash=1000.0,
        solvency=True,
    )
    agents = {"agent_1": agent}
    companies = {"comp_1": comp}

    summary = bank.service_daily_banking(agents, companies, current_tick=1)

    # Deposit interest was paid
    assert summary["interest_paid"] > 0.0
    assert bank.deposits["agent_1"] > 10_000.0
    assert agent.bank_deposit == bank.deposits["agent_1"]

    # Loan interest & amortization were collected
    assert summary["interest_collected"] > 0.0
    assert bank.loans["comp_1"] < 5_000.0
    assert comp.cash < 1000.0


def test_bank_bad_debt_writeoff():
    bank = MunicipalBank(cash_reserves=50_000.0)
    bank.loans["comp_bankrupt"] = 8_000.0

    comp = Company(
        id="comp_bankrupt",
        name="Failed Co",
        district_id="dist_0",
        commodity_type=CommodityType.FOOD,
        cash=0.0,
        solvency=False,  # Insolvent
    )

    summary = bank.service_daily_banking(
        agents={}, companies={"comp_bankrupt": comp}, current_tick=1
    )

    # Bad debt was written down
    assert "comp_bankrupt" not in bank.loans
    assert summary["bad_debt_writeoffs"] == 8_000.0
    assert bank.accumulated_bad_debt_writeoffs == 8_000.0
