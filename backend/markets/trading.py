"""HIVEMIND Agent Equity Trading & Market Participation Module."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from backend.agents.roles import RoleType
from backend.markets.order_book import Order, OrderBook, OrderSide, OrderType, Trade

if TYPE_CHECKING:
    from backend.agents.agent import Agent
    from backend.companies.company import Company
    from backend.markets.equities import ShareRegistry


def calculate_fundamental_value(company: Company) -> float:
    """Estimate per-share fundamental book value: (Capital + Cash - Debt) / Shares."""
    shares = getattr(company, "shares_outstanding", 10_000)
    debt = getattr(company, "bank_loan", 0.0)
    net_equity = max(10_000.0, company.capital + company.cash - debt)
    return round(net_equity / max(shares, 1), 2)


def execute_daily_equity_trading(
    order_books: dict[str, OrderBook],
    registry: ShareRegistry,
    agents: dict[str, Agent],
    companies: dict[str, Company],
    rng: random.Random,
    current_tick: int,
) -> list[Trade]:
    """
    Execute daily agent equity trading rounds:
    1. Agents evaluate stock fundamental valuations based on corporate balance sheets.
    2. Wealthy agents and Investors submit limit buy orders.
    3. Cash-constrained agents submit limit sell orders.
    4. Match orders through continuous double auction order books.
    5. Settle stock transfers and currency debits/credits.
    """
    all_executed_trades: list[Trade] = []

    # Map tickers to company objects
    ticker_to_comp: dict[str, Company] = {}
    for comp in companies.values():
        ticker = registry.get_company_ticker(comp.id)
        if ticker:
            ticker_to_comp[ticker] = comp

    for ticker, ob in order_books.items():
        comp = ticker_to_comp.get(ticker)
        if not comp:
            continue

        fair_val = calculate_fundamental_value(comp)
        current_market_price = ob.last_price

        # 1. Generate Buy Orders from agents with surplus liquidity
        prospective_buyers = [
            a
            for a in agents.values()
            if a.alive
            and (
                a.role in (RoleType.INVESTOR, RoleType.BUSINESS_OWNER)
                or (a.cash > 2500.0 and a.personality.risk_tolerance > 0.35)
            )
        ]
        rng.shuffle(prospective_buyers)

        for buyer in prospective_buyers[:4]:
            # Buy if market price is attractive relative to fundamental value
            if current_market_price <= fair_val * 1.15 and buyer.cash > 500.0:
                alloc_cash = min(buyer.cash * 0.20, 1000.0)
                bid_price = round(
                    max(1.0, current_market_price * rng.uniform(0.98, 1.03)), 2
                )
                max_shares = int(alloc_cash / max(bid_price, 1.0))
                if max_shares > 0:
                    buy_order = Order(
                        id=f"ord_buy_{buyer.id}_{ticker}_{current_tick}",
                        trader_id=buyer.id,
                        ticker=ticker,
                        side=OrderSide.BUY,
                        order_type=OrderType.LIMIT,
                        price=bid_price,
                        quantity=max_shares,
                        created_tick=current_tick,
                    )
                    trades = ob.place_order(buy_order, current_tick)
                    all_executed_trades.extend(trades)

        # 2. Generate Sell Orders from agents holding shares who need cash or rebalance
        equity = registry.get_equity(ticker)
        if not equity:
            continue

        for holder_id, share_count in list(equity.shareholders.items()):
            if share_count <= 0 or holder_id not in agents:
                continue

            seller = agents[holder_id]
            if not seller.alive:
                continue

            # Sell if low on cash (liquidity need) or price exceeds fair value (profit taking)
            wants_to_sell = (
                seller.cash < 600.0  # Liquidity distress
                or current_market_price >= fair_val * 1.25  # Profit taking
                or rng.random() < 0.05  # General portfolio rebalancing
            )

            if wants_to_sell:
                sell_qty = max(
                    1, min(share_count, int(share_count * rng.uniform(0.1, 0.4)))
                )
                ask_price = round(
                    max(1.0, current_market_price * rng.uniform(0.97, 1.02)), 2
                )
                sell_order = Order(
                    id=f"ord_sell_{seller.id}_{ticker}_{current_tick}",
                    trader_id=seller.id,
                    ticker=ticker,
                    side=OrderSide.SELL,
                    order_type=OrderType.LIMIT,
                    price=ask_price,
                    quantity=sell_qty,
                    created_tick=current_tick,
                )
                trades = ob.place_order(sell_order, current_tick)
                all_executed_trades.extend(trades)

    # 3. Settle all executed trades: Cash and Share transfers
    for trade in all_executed_trades:
        trade_cost = trade.turnover
        buyer = agents.get(trade.buyer_id)
        seller = agents.get(trade.seller_id)

        # Transfer shares in registry
        registry.transfer_shares(
            trade.ticker, trade.seller_id, trade.buyer_id, trade.quantity
        )

        # Transfer cash between agents
        if buyer:
            buyer.cash = max(0.0, buyer.cash - trade_cost)
            buyer.portfolio[trade.ticker] = (
                buyer.portfolio.get(trade.ticker, 0) + trade.quantity
            )
        if seller:
            seller.cash += trade_cost
            if trade.ticker in seller.portfolio:
                seller.portfolio[trade.ticker] = max(
                    0, seller.portfolio[trade.ticker] - trade.quantity
                )

    return all_executed_trades
