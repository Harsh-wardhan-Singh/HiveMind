"""HIVEMIND Continuous Double Auction Order Book Module."""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"


@dataclass
class Order:
    id: str
    trader_id: str
    ticker: str
    side: OrderSide
    order_type: OrderType
    price: float  # Limit price (or reference price for market orders)
    quantity: int
    filled_quantity: int = 0
    created_tick: int = 0

    @property
    def remaining_quantity(self) -> int:
        return max(0, self.quantity - self.filled_quantity)

    @property
    def is_filled(self) -> bool:
        return self.filled_quantity >= self.quantity

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "trader_id": self.trader_id,
            "ticker": self.ticker,
            "side": self.side.value,
            "order_type": self.order_type.value,
            "price": round(self.price, 2),
            "quantity": self.quantity,
            "filled_quantity": self.filled_quantity,
            "remaining_quantity": self.remaining_quantity,
            "created_tick": self.created_tick,
        }


@dataclass(frozen=True)
class Trade:
    id: str
    ticker: str
    buyer_id: str
    seller_id: str
    price: float
    quantity: int
    tick: int

    @property
    def turnover(self) -> float:
        return round(self.price * self.quantity, 2)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "ticker": self.ticker,
            "buyer_id": self.buyer_id,
            "seller_id": self.seller_id,
            "price": round(self.price, 2),
            "quantity": self.quantity,
            "turnover": self.turnover,
            "tick": self.tick,
        }


class OrderBook:
    """
    Continuous double auction order book enforcing price-time priority.
    - Bids sorted by price DESCENDING, then created_tick ASCENDING.
    - Asks sorted by price ASCENDING, then created_tick ASCENDING.
    """

    def __init__(self, ticker: str, initial_price: float = 10.0) -> None:
        self.ticker = ticker
        self.bids: list[Order] = []
        self.asks: list[Order] = []
        self.last_price: float = initial_price
        self.daily_volume: int = 0
        self.daily_turnover: float = 0.0
        self.trades_history: list[Trade] = []

    @property
    def best_bid(self) -> float | None:
        return self.bids[0].price if self.bids else None

    @property
    def best_ask(self) -> float | None:
        return self.asks[0].price if self.asks else None

    @property
    def spread(self) -> float | None:
        if self.best_bid is not None and self.best_ask is not None:
            return round(self.best_ask - self.best_bid, 4)
        return None

    @property
    def vwap(self) -> float:
        """Volume-Weighted Average Price for the current trading day."""
        if self.daily_volume <= 0:
            return self.last_price
        return round(self.daily_turnover / self.daily_volume, 4)

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order by ID from bids or asks."""
        for i, order in enumerate(self.bids):
            if order.id == order_id:
                self.bids.pop(i)
                return True
        for i, order in enumerate(self.asks):
            if order.id == order_id:
                self.asks.pop(i)
                return True
        return False

    def place_order(self, order: Order, current_tick: int) -> list[Trade]:
        """
        Match incoming order against resting opposite-side book.
        Executes trades at the maker's (resting order) price.
        Unfilled limit order remainder rests on the book.
        """
        executed_trades: list[Trade] = []

        if order.side == OrderSide.BUY:
            # Match against asks (lowest price first)
            while self.asks and order.remaining_quantity > 0:
                best_ask = self.asks[0]
                # Price matching condition
                if order.order_type == OrderType.LIMIT and order.price < best_ask.price:
                    break  # Highest willing bid is below lowest ask

                match_qty = min(order.remaining_quantity, best_ask.remaining_quantity)
                match_price = best_ask.price  # Maker price

                trade = Trade(
                    id=f"tr_{self.ticker}_{current_tick}_{len(self.trades_history) + 1}",
                    ticker=self.ticker,
                    buyer_id=order.trader_id,
                    seller_id=best_ask.trader_id,
                    price=match_price,
                    quantity=match_qty,
                    tick=current_tick,
                )

                order.filled_quantity += match_qty
                best_ask.filled_quantity += match_qty
                self.last_price = match_price
                self.daily_volume += match_qty
                self.daily_turnover += match_qty * match_price

                executed_trades.append(trade)
                self.trades_history.append(trade)

                if best_ask.is_filled:
                    self.asks.pop(0)

            # Insert remaining limit buy order into bids
            if order.remaining_quantity > 0 and order.order_type == OrderType.LIMIT:
                self._insert_bid(order)

        elif order.side == OrderSide.SELL:
            # Match against bids (highest price first)
            while self.bids and order.remaining_quantity > 0:
                best_bid = self.bids[0]
                # Price matching condition
                if order.order_type == OrderType.LIMIT and order.price > best_bid.price:
                    break  # Lowest willing ask is above highest bid

                match_qty = min(order.remaining_quantity, best_bid.remaining_quantity)
                match_price = best_bid.price  # Maker price

                trade = Trade(
                    id=f"tr_{self.ticker}_{current_tick}_{len(self.trades_history) + 1}",
                    ticker=self.ticker,
                    buyer_id=best_bid.trader_id,
                    seller_id=order.trader_id,
                    price=match_price,
                    quantity=match_qty,
                    tick=current_tick,
                )

                order.filled_quantity += match_qty
                best_bid.filled_quantity += match_qty
                self.last_price = match_price
                self.daily_volume += match_qty
                self.daily_turnover += match_qty * match_price

                executed_trades.append(trade)
                self.trades_history.append(trade)

                if best_bid.is_filled:
                    self.bids.pop(0)

            # Insert remaining limit sell order into asks
            if order.remaining_quantity > 0 and order.order_type == OrderType.LIMIT:
                self._insert_ask(order)

        return executed_trades

    def _insert_bid(self, order: Order) -> None:
        """Insert bid maintaining price DESCENDING, created_tick ASCENDING."""
        idx = 0
        while idx < len(self.bids):
            existing = self.bids[idx]
            if order.price > existing.price:
                break
            if (
                order.price == existing.price
                and order.created_tick < existing.created_tick
            ):
                break
            idx += 1
        self.bids.insert(idx, order)

    def _insert_ask(self, order: Order) -> None:
        """Insert ask maintaining price ASCENDING, created_tick ASCENDING."""
        idx = 0
        while idx < len(self.asks):
            existing = self.asks[idx]
            if order.price < existing.price:
                break
            if (
                order.price == existing.price
                and order.created_tick < existing.created_tick
            ):
                break
            idx += 1
        self.asks.insert(idx, order)

    def reset_daily_stats(self) -> None:
        """Reset daily volume and turnover counters for the new tick."""
        self.daily_volume = 0
        self.daily_turnover = 0.0

    def get_depth(self, levels: int = 5) -> dict[str, list[dict[str, Any]]]:
        """Return top N levels of bids and asks."""
        bids_depth = [
            {"price": round(b.price, 2), "quantity": b.remaining_quantity}
            for b in self.bids[:levels]
        ]
        asks_depth = [
            {"price": round(a.price, 2), "quantity": a.remaining_quantity}
            for a in self.asks[:levels]
        ]
        return {"bids": bids_depth, "asks": asks_depth}

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "last_price": round(self.last_price, 2),
            "best_bid": round(self.best_bid, 2) if self.best_bid is not None else None,
            "best_ask": round(self.best_ask, 2) if self.best_ask is not None else None,
            "spread": round(self.spread, 2) if self.spread is not None else None,
            "daily_volume": self.daily_volume,
            "daily_turnover": round(self.daily_turnover, 2),
            "vwap": round(self.vwap, 2),
            "bids_count": len(self.bids),
            "asks_count": len(self.asks),
        }
