"""Unit tests for Continuous Double Auction Order Book."""

from backend.markets.order_book import Order, OrderBook, OrderSide, OrderType


def test_order_book_initial_state():
    ob = OrderBook(ticker="FOOD", initial_price=10.0)
    assert ob.ticker == "FOOD"
    assert ob.last_price == 10.0
    assert ob.best_bid is None
    assert ob.best_ask is None
    assert ob.spread is None
    assert ob.daily_volume == 0


def test_limit_order_placement_and_spread():
    ob = OrderBook(ticker="FOOD", initial_price=10.0)

    # Place bid: 100 shares @ 9.50
    bid = Order(
        id="ord_1",
        trader_id="agent_1",
        ticker="FOOD",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        price=9.50,
        quantity=100,
        created_tick=1,
    )
    trades = ob.place_order(bid, current_tick=1)
    assert len(trades) == 0
    assert ob.best_bid == 9.50
    assert ob.best_ask is None

    # Place ask: 50 shares @ 10.50
    ask = Order(
        id="ord_2",
        trader_id="agent_2",
        ticker="FOOD",
        side=OrderSide.SELL,
        order_type=OrderType.LIMIT,
        price=10.50,
        quantity=50,
        created_tick=1,
    )
    trades = ob.place_order(ask, current_tick=1)
    assert len(trades) == 0
    assert ob.best_ask == 10.50
    assert ob.spread == 1.00


def test_full_trade_execution():
    ob = OrderBook(ticker="FOOD", initial_price=10.0)

    # Resting ask: 100 shares @ 10.00
    ask = Order(
        id="ask_1",
        trader_id="seller_1",
        ticker="FOOD",
        side=OrderSide.SELL,
        order_type=OrderType.LIMIT,
        price=10.00,
        quantity=100,
        created_tick=1,
    )
    ob.place_order(ask, current_tick=1)

    # Incoming matching bid: 100 shares @ 10.00
    bid = Order(
        id="bid_1",
        trader_id="buyer_1",
        ticker="FOOD",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        price=10.00,
        quantity=100,
        created_tick=1,
    )
    trades = ob.place_order(bid, current_tick=1)

    assert len(trades) == 1
    t = trades[0]
    assert t.price == 10.00
    assert t.quantity == 100
    assert t.buyer_id == "buyer_1"
    assert t.seller_id == "seller_1"
    assert t.turnover == 1000.00
    assert ob.daily_volume == 100
    assert ob.last_price == 10.00
    assert ob.best_bid is None
    assert ob.best_ask is None


def test_partial_fill_and_price_time_priority():
    ob = OrderBook(ticker="FOOD", initial_price=10.0)

    # Two resting asks: ask1 @ 10.00 (qty 40, tick 1), ask2 @ 10.00 (qty 60, tick 2)
    ask1 = Order(
        id="ask_1",
        trader_id="seller_1",
        ticker="FOOD",
        side=OrderSide.SELL,
        order_type=OrderType.LIMIT,
        price=10.00,
        quantity=40,
        created_tick=1,
    )
    ask2 = Order(
        id="ask_2",
        trader_id="seller_2",
        ticker="FOOD",
        side=OrderSide.SELL,
        order_type=OrderType.LIMIT,
        price=10.00,
        quantity=60,
        created_tick=2,
    )
    ob.place_order(ask1, current_tick=1)
    ob.place_order(ask2, current_tick=2)

    # Incoming large bid: 70 shares @ 10.50
    bid = Order(
        id="bid_1",
        trader_id="buyer_1",
        ticker="FOOD",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        price=10.50,
        quantity=70,
        created_tick=3,
    )
    trades = ob.place_order(bid, current_tick=3)

    assert len(trades) == 2
    # First match with ask1 (older order) for 40
    assert trades[0].seller_id == "seller_1"
    assert trades[0].quantity == 40
    # Second match with ask2 for remaining 30
    assert trades[1].seller_id == "seller_2"
    assert trades[1].quantity == 30

    # Remaining on ask2: 30 shares
    assert ob.best_ask == 10.00
    assert ob.asks[0].remaining_quantity == 30
    assert ob.daily_volume == 70
    assert ob.vwap == 10.00


def test_cancel_order():
    ob = OrderBook(ticker="FOOD", initial_price=10.0)
    bid = Order(
        id="bid_cancel",
        trader_id="buyer_1",
        ticker="FOOD",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        price=9.00,
        quantity=50,
        created_tick=1,
    )
    ob.place_order(bid, current_tick=1)
    assert ob.best_bid == 9.00

    cancelled = ob.cancel_order("bid_cancel")
    assert cancelled is True
    assert ob.best_bid is None
    assert ob.cancel_order("non_existent") is False
