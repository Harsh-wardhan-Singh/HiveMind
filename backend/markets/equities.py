"""HIVEMIND Corporate Equities & Share Registry Module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from backend.agents.agent import Agent
    from backend.companies.company import Company


@dataclass
class EquityShare:
    ticker: str
    company_id: str
    total_shares: int = 10_000
    par_value: float = 10.0
    shareholders: dict[str, int] = field(default_factory=dict)
    dividend_per_share: float = 0.0
    total_dividends_paid: float = 0.0

    def get_holder_shares(self, holder_id: str) -> int:
        return self.shareholders.get(holder_id, 0)

    def transfer(self, from_id: str, to_id: str, quantity: int) -> bool:
        if quantity <= 0:
            return False
        sender_bal = self.get_holder_shares(from_id)
        if sender_bal < quantity:
            return False

        self.shareholders[from_id] = sender_bal - quantity
        if self.shareholders[from_id] == 0:
            del self.shareholders[from_id]

        self.shareholders[to_id] = self.shareholders.get(to_id, 0) + quantity
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "company_id": self.company_id,
            "total_shares": self.total_shares,
            "par_value": round(self.par_value, 2),
            "shareholder_count": len(self.shareholders),
            "dividend_per_share": round(self.dividend_per_share, 4),
            "total_dividends_paid": round(self.total_dividends_paid, 2),
        }


class ShareRegistry:
    """Registry managing corporate equity issuance, cap tables, and dividend distributions."""

    def __init__(self) -> None:
        self.equities: dict[str, EquityShare] = {}

    def issue_shares(
        self,
        company_id: str,
        ticker: str,
        total_shares: int = 10_000,
        initial_holders: dict[str, int] | None = None,
    ) -> EquityShare:
        """Issue shares for a newly registered corporate firm."""
        holders = dict(initial_holders or {})
        equity = EquityShare(
            ticker=ticker,
            company_id=company_id,
            total_shares=total_shares,
            shareholders=holders,
        )
        self.equities[ticker] = equity
        return equity

    def get_equity(self, ticker: str) -> EquityShare | None:
        return self.equities.get(ticker)

    def get_company_ticker(self, company_id: str) -> str | None:
        for ticker, eq in self.equities.items():
            if eq.company_id == company_id:
                return ticker
        return None

    def transfer_shares(
        self,
        ticker: str,
        from_id: str,
        to_id: str,
        quantity: int,
    ) -> bool:
        """Transfer share ownership between two parties."""
        eq = self.get_equity(ticker)
        if not eq:
            return False
        return eq.transfer(from_id, to_id, quantity)

    def declare_and_distribute_dividends(
        self,
        company: Company,
        agents: dict[str, Agent],
        payout_ratio: float = 0.35,
    ) -> float:
        """
        Distribute a fraction of daily corporate net profits to shareholders.
        Requires company to be solvent, profitable, and retain adequate operating cash.
        Returns total dividend currency paid.
        """
        if not company.solvency or company.daily_profit <= 0.0 or company.cash < 5000.0:
            return 0.0

        ticker = self.get_company_ticker(company.id)
        if not ticker:
            return 0.0

        equity = self.equities[ticker]
        # Payout capped at 35% of profit and max 15% of cash reserves
        total_dividend = min(company.daily_profit * payout_ratio, company.cash * 0.15)
        if total_dividend <= 0.0 or equity.total_shares <= 0:
            return 0.0

        div_per_share = total_dividend / equity.total_shares
        equity.dividend_per_share = div_per_share

        actual_paid = 0.0
        for holder_id, shares in list(equity.shareholders.items()):
            if shares <= 0:
                continue
            payout = div_per_share * shares
            if holder_id in agents and agents[holder_id].alive:
                agents[holder_id].cash += payout
                actual_paid += payout
            elif holder_id.startswith("comp_"):
                # Corporate shareholder holding shares in another firm
                pass

        company.cash -= actual_paid
        equity.total_dividends_paid += actual_paid
        return actual_paid

    def to_dict(self) -> dict[str, Any]:
        return {ticker: eq.to_dict() for ticker, eq in self.equities.items()}

