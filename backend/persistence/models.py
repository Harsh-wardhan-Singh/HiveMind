"""HIVEMIND Persistence Database Models."""

from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class RunModel(Base):
    __tablename__ = "runs"

    run_id = Column(String, primary_key=True)
    seed = Column(Integer, nullable=False)
    name = Column(String, nullable=True)
    total_days = Column(Integer, nullable=False)
    status = Column(String, default="INITIALIZED")
    parent_run_id = Column(String, nullable=True, index=True)
    fork_tick = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class EventModel(Base):
    __tablename__ = "events"

    event_id = Column(String, primary_key=True)
    run_id = Column(String, nullable=False, index=True)
    tick = Column(Integer, nullable=False, index=True)
    event_type = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class SnapshotModel(Base):
    __tablename__ = "snapshots"

    snapshot_id = Column(String, primary_key=True)
    run_id = Column(String, nullable=False, index=True)
    tick = Column(Integer, nullable=False, index=True)
    state_blob = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
