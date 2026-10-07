"""Integration tests for Phase 3 Production, Goods, Labor & Inflation Economy."""

from backend.app.config import CityConfig, SimulationConfig
from backend.economy.goods import CommodityType
from backend.simulation.engine import SimulationEngine


def test_economic_initialization(base_config):
    with SimulationEngine(base_config) as engine:
        state = engine.state

        # Check companies initialized across commodity sectors
        assert len(state.companies) == 9
        sectors = {comp.commodity_type for comp in state.companies.values()}
        assert CommodityType.FOOD in sectors
        assert CommodityType.HOUSING in sectors
        assert CommodityType.HEALTHCARE in sectors
        assert CommodityType.CONSUMER_GOODS in sectors

        # Check market initialized
        assert len(state.market.prices) == 4
        for c_type in CommodityType:
            assert state.market.prices[c_type] > 0.0

        # Check metrics macroeconomic fields
        metrics = state.metrics
        assert metrics.cpi == 100.0
        assert metrics.inflation_rate == 0.0
        assert 0.0 <= metrics.unemployment_rate <= 1.0
        assert metrics.gdp >= 0.0
        assert metrics.average_wage >= 0.0


def test_economic_multi_day_run(base_config):
    with SimulationEngine(base_config) as engine:
        state = engine.state

        # Run 30 days
        for _ in range(30):
            engine.step()

        assert state.clock.current_tick == 30

        # Verify economic activity occurred
        # 1. Companies produced goods and paid wages
        for comp in state.companies.values():
            assert comp.capital > 0.0
            # Some inventory should be produced/remaining
            assert comp.inventory >= 0.0

        # 2. Market prices adjusted dynamically
        for c_type in CommodityType:
            price = state.market.prices[c_type]
            assert price > 0.0

        # 3. CPI was tracked
        assert 10.0 <= state.metrics.cpi <= 300.0

        # 4. GDP is positive
        assert state.metrics.gdp > 0.0

        # 5. Check events emitted
        events = engine.event_store.get_events(engine.run_id)
        event_types = {e.event_type for e in events}
        assert "CompanyFounded" in event_types
        assert "AgentEmployed" in event_types
        assert "DayTicked" in event_types


def test_economic_strict_determinism(temp_db_url):
    """Verify bit-for-bit economic determinism under identical seeds."""
    cfg1 = SimulationConfig(
        run_id="econ_det_1",
        seed=998877,
        total_days=20,
        snapshot_interval_days=10,
        database_url=temp_db_url,
        city=CityConfig(starting_population=20),
    )
    cfg2 = SimulationConfig(
        run_id="econ_det_2",
        seed=998877,
        total_days=20,
        snapshot_interval_days=10,
        database_url=temp_db_url,
        city=CityConfig(starting_population=20),
    )

    with SimulationEngine(cfg1) as engine1:
        for _ in range(20):
            engine1.step()
        state1 = engine1.state

    with SimulationEngine(cfg2) as engine2:
        for _ in range(20):
            engine2.step()
        state2 = engine2.state

    # 1. Compare Commodity Market Prices
    for c_type in CommodityType:
        assert state1.market.prices[c_type] == state2.market.prices[c_type]
        assert state1.market.sales[c_type] == state2.market.sales[c_type]

    # 2. Compare Company balances and inventories
    for c_id in state1.companies:
        c1 = state1.companies[c_id]
        c2 = state2.companies[c_id]
        assert c1.cash == c2.cash
        assert c1.inventory == c2.inventory
        assert c1.daily_revenue == c2.daily_revenue
        assert c1.daily_expenses == c2.daily_expenses

    # 3. Compare Macroeconomic Telemetry
    m1 = state1.metrics
    m2 = state2.metrics
    assert m1.gdp == m2.gdp
    assert m1.cpi == m2.cpi
    assert m1.inflation_rate == m2.inflation_rate
    assert m1.unemployment_rate == m2.unemployment_rate
    assert m1.average_wage == m2.average_wage
