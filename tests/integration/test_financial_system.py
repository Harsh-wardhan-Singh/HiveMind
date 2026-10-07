"""Integration tests for Phase 4 Markets, Equities, Order Books & Banking."""

from backend.app.config import CityConfig, SimulationConfig
from backend.simulation.engine import SimulationEngine


def test_financial_system_initialization(base_config):
    with SimulationEngine(base_config) as engine:
        state = engine.state

        # 1. Equities Registry
        assert len(state.share_registry.equities) == 9
        tickers = set(state.share_registry.equities.keys())
        assert "AGRI" in tickers
        assert "FOOD" in tickers
        assert "HOUS" in tickers
        assert "HLTH" in tickers
        assert "METL" in tickers

        # 2. Order Books
        assert len(state.order_books) == 9
        for ob in state.order_books.values():
            assert ob.last_price == 10.0

        # 3. Municipal Bank
        assert state.bank.cash_reserves > 0.0
        assert state.bank.total_deposits > 0.0

        # 4. Metrics Telemetry
        metrics = state.metrics
        # 9 companies * 10,000 shares * 10.0 price = 900,000.0 market cap
        assert metrics.stock_market_cap >= 900_000.0
        assert metrics.total_bank_deposits > 0.0
        assert metrics.bank_reserves > 0.0


def test_financial_multi_day_run(base_config):
    with SimulationEngine(base_config) as engine:
        # Run 30 days
        for _ in range(30):
            engine.step()

        state = engine.state
        assert state.clock.current_tick == 30

        # 1. Verify banking activity
        assert state.bank.total_deposits > 0.0
        assert state.bank.cash_reserves > 0.0

        # 2. Verify stock market metrics
        assert state.metrics.stock_market_cap > 0.0

        # 3. Verify event store captured equity trades or financial activity
        events = engine.event_store.get_events(engine.run_id)
        event_types = {e.event_type for e in events}
        assert "CompanyFounded" in event_types
        assert "DayTicked" in event_types


def test_financial_strict_determinism(temp_db_url):
    """Verify bit-for-bit determinism across equity and banking systems under identical seeds."""
    cfg1 = SimulationConfig(
        run_id="fin_det_1",
        seed=776655,
        total_days=25,
        snapshot_interval_days=10,
        database_url=temp_db_url,
        city=CityConfig(starting_population=20),
    )
    cfg2 = SimulationConfig(
        run_id="fin_det_2",
        seed=776655,
        total_days=25,
        snapshot_interval_days=10,
        database_url=temp_db_url,
        city=CityConfig(starting_population=20),
    )

    with SimulationEngine(cfg1) as engine1:
        for _ in range(25):
            engine1.step()
        state1 = engine1.state

    with SimulationEngine(cfg2) as engine2:
        for _ in range(25):
            engine2.step()
        state2 = engine2.state

    # 1. Compare Order Book stock prices
    for ticker in state1.order_books:
        ob1 = state1.order_books[ticker]
        ob2 = state2.order_books[ticker]
        assert ob1.last_price == ob2.last_price
        assert ob1.daily_volume == ob2.daily_volume
        assert ob1.vwap == ob2.vwap

    # 2. Compare Bank Ledgers
    assert state1.bank.total_deposits == state2.bank.total_deposits
    assert state1.bank.total_loans == state2.bank.total_loans
    assert state1.bank.cash_reserves == state2.bank.cash_reserves

    # 3. Compare Shareholder registries
    for ticker in state1.share_registry.equities:
        eq1 = state1.share_registry.equities[ticker]
        eq2 = state2.share_registry.equities[ticker]
        assert eq1.total_dividends_paid == eq2.total_dividends_paid
        assert eq1.shareholders == eq2.shareholders

    # 4. Compare Aggregate Metrics
    m1 = state1.metrics
    m2 = state2.metrics
    assert m1.stock_market_cap == m2.stock_market_cap
    assert m1.total_bank_deposits == m2.total_bank_deposits
    assert m1.total_bank_loans == m2.total_bank_loans
    assert m1.daily_dividends_paid == m2.daily_dividends_paid
    assert m1.gdp == m2.gdp
    assert m1.cpi == m2.cpi

