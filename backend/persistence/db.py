"""HIVEMIND Database Session and Initialization Module."""

from collections.abc import Callable

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from backend.persistence.models import Base

_global_engine: Engine | None = None
_global_session_factory: Callable[[], Session] | None = None


def create_db_engine_and_factory(
    database_url: str = "sqlite:///hivemind.db",
) -> tuple[Engine, Callable[[], Session]]:
    """Create a new engine and session factory for a specific database URL."""
    connect_args = (
        {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    )
    engine = create_engine(database_url, connect_args=connect_args)
    Base.metadata.create_all(engine)
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, factory


def init_db(database_url: str = "sqlite:///hivemind.db") -> Engine:
    """Initialize the default global database."""
    global _global_engine, _global_session_factory
    _global_engine, _global_session_factory = create_db_engine_and_factory(database_url)
    return _global_engine


def get_db_session() -> Session:
    """Retrieve a session from the default global session factory."""
    if _global_session_factory is None:
        init_db()
    return _global_session_factory()
