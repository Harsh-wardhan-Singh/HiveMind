"""HIVEMIND Municipal Commercial Bank & Credit Engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from backend.agents.agent import Agent
    from backend.companies.company import Company


@dataclass
class MunicipalBank:
    id: str = "bank_municipal_01"
    name: str = "Hivemind Municipal Commercial Bank"
    cash_reserves: float = 150_000.0
    reserve_ratio: float = 0.10  # 10% statutory fractional reserve
    deposit_annual_rate: float = 0.03  # 3% annual interest on savings
    loan_annual_rate: float = 0.07  # 7% annual interest on loans
    deposits: dict[str, float] = field(default_factory=dict)
    loans: dict[str, float] = field(default_factory=dict)
    daily_interest_paid: float = 0.0
    daily_interest_collected: float = 0.0
    accumulated_bad_debt_writeoffs: float = 0.0

    @property
    def total_deposits(self) -> float:
        return round(sum(self.deposits.values()), 2)

    @property
    def total_loans(self) -> float:
        return round(sum(self.loans.values()), 2)

    @property
    def reserve_requirement(self) -> float:
        return round(self.total_deposits * self.reserve_ratio, 2)

    @property
    def excess_reserves(self) -> float:
        return round(self.cash_reserves - self.reserve_requirement, 2)

    def deposit(self, account_id: str, amount: float) -> float:
        """Accept cash deposit into interest-bearing account."""
        if amount <= 0.0:
            return 0.0
        self.deposits[account_id] = self.deposits.get(account_id, 0.0) + amount
        self.cash_reserves += amount
        return amount

    def withdraw(self, account_id: str, amount: float) -> float:
        """Withdraw cash from deposit account."""
        if amount <= 0.0 or account_id not in self.deposits:
            return 0.0
        current_bal = self.deposits[account_id]
        actual_withdraw = min(amount, current_bal, self.cash_reserves)
        if actual_withdraw <= 0.0:
            return 0.0

        self.deposits[account_id] -= actual_withdraw
        if self.deposits[account_id] <= 0.001:
            del self.deposits[account_id]
        self.cash_reserves -= actual_withdraw
        return actual_withdraw

    def apply_for_loan(
        self,
        borrower_id: str,
        requested_amount: float,
        collateral_value: float,
    ) -> bool:
        """
        Underwrite commercial or personal loan:
        1. Fractional reserve check: bank must maintain reserve_ratio after disbursement.
        2. Collateral check: collateral must cover at least 35% of requested principal.
        """
        if requested_amount <= 0.0:
            return False

        # Check reserve health
        post_loan_reserves = self.cash_reserves - requested_amount
        required_post_reserves = (self.total_deposits) * self.reserve_ratio
        if post_loan_reserves < required_post_reserves:
            return False

        # Collateral / debt-service capacity
        if collateral_value < requested_amount * 0.35:
            return False

        self.loans[borrower_id] = self.loans.get(borrower_id, 0.0) + requested_amount
        self.cash_reserves -= requested_amount
        return True

    def service_daily_banking(
        self,
        agents: dict[str, Agent],
        companies: dict[str, Company],
        current_tick: int,
    ) -> dict[str, float]:
        """
        Execute daily banking ledger operations:
        1. Pay daily deposit interest to depositors.
        2. Collect daily loan interest and amortize loan principal from borrowers.
        3. Write down bad debt from insolvent companies.
        """
        daily_r_dep = (1.0 + self.deposit_annual_rate) ** (1.0 / 365.25) - 1.0
        daily_r_loan = (1.0 + self.loan_annual_rate) ** (1.0 / 365.25) - 1.0

        # 1. Deposit interest accrual
        total_interest_paid_today = 0.0
        for acc_id, balance in list(self.deposits.items()):
            if balance <= 0.0:
                continue
            interest = balance * daily_r_dep
            self.deposits[acc_id] += interest
            self.cash_reserves -= interest
            total_interest_paid_today += interest
            # Sync with agent balance if individual
            if acc_id in agents:
                agents[acc_id].bank_deposit = self.deposits[acc_id]

        self.daily_interest_paid = total_interest_paid_today

        # 2. Loan interest collection & principal amortization
        total_interest_collected_today = 0.0
        for borrower_id, principal in list(self.loans.items()):
            if principal <= 0.0:
                del self.loans[borrower_id]
                continue

            interest_due = principal * daily_r_loan
            amortization = principal * 0.001  # 0.1% daily repayment (~36.5% annually)
            total_due = interest_due + amortization

            # Find debtor entity
            borrower_obj = agents.get(borrower_id) or companies.get(borrower_id)
            if not borrower_obj:
                continue

            if borrower_obj.cash >= total_due:
                borrower_obj.cash -= total_due
                self.cash_reserves += total_due
                new_principal = max(0.0, principal - amortization)
                self.loans[borrower_id] = new_principal
                total_interest_collected_today += interest_due
                if hasattr(borrower_obj, "bank_loan"):
                    borrower_obj.bank_loan = new_principal
            else:
                # Debt distress / insolvency check
                if hasattr(borrower_obj, "solvency") and not borrower_obj.solvency:
                    # Orderly write-down of bankrupt corporate debt
                    written_off = self.loans.pop(borrower_id, 0.0)
                    self.accumulated_bad_debt_writeoffs += written_off
                    if hasattr(borrower_obj, "bank_loan"):
                        borrower_obj.bank_loan = 0.0

        self.daily_interest_collected = total_interest_collected_today

        return {
            "interest_paid": round(self.daily_interest_paid, 2),
            "interest_collected": round(self.daily_interest_collected, 2),
            "total_deposits": self.total_deposits,
            "total_loans": self.total_loans,
            "excess_reserves": self.excess_reserves,
            "bad_debt_writeoffs": round(self.accumulated_bad_debt_writeoffs, 2),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "cash_reserves": round(self.cash_reserves, 2),
            "total_deposits": self.total_deposits,
            "total_loans": self.total_loans,
            "reserve_ratio": self.reserve_ratio,
            "reserve_requirement": self.reserve_requirement,
            "excess_reserves": self.excess_reserves,
            "daily_interest_paid": round(self.daily_interest_paid, 2),
            "daily_interest_collected": round(self.daily_interest_collected, 2),
            "accumulated_bad_debt_writeoffs": round(
                self.accumulated_bad_debt_writeoffs, 2
            ),
            "depositor_count": len(self.deposits),
            "borrower_count": len(self.loans),
        }
