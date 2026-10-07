"""HIVEMIND Test Suite Fixtures."""

import gc
import os
import tempfile

import pytest

from backend.app.config import CityConfig, SimulationConfig
from backend.persistence.db import init_db


@pytest.fixture
def temp_db_url():
    """Create a temporary SQLite database URL for isolated test execution."""
    fd, temp_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db_url = f"sqlite:///{temp_path}"
    engine = init_db(db_url)
    yield db_url
    engine.dispose()
    gc.collect()
    if os.path.exists(temp_path):
        try:
            os.remove(temp_path)
        except PermissionError:
            pass


@pytest.fixture
def base_config(temp_db_url):
    """Fixture providing a standard test configuration."""
    return SimulationConfig(
        run_id="test_run_01",
        seed=12345,
        total_days=30,
        snapshot_interval_days=10,
        database_url=temp_db_url,
        city=CityConfig(starting_population=20),
    )
