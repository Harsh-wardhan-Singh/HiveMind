"""HIVEMIND Append-Only Event Store and Snapshot Engine."""

from typing import Any

from sqlalchemy.orm import Session

from backend.events.event_types import Event
from backend.persistence.db import get_db_session
from backend.persistence.models import EventModel, RunModel, SnapshotModel


class EventStore:
    """Manages immutable persistence of events and periodic state snapshots."""

    def __init__(self, session_factory=get_db_session):
        self._get_session = session_factory

    def record_run(
        self, run_id: str, seed: int, total_days: int, name: str | None = None
    ) -> None:
        """Register a new simulation run in the database."""
        session: Session = self._get_session()
        try:
            run = RunModel(
                run_id=run_id,
                seed=seed,
                total_days=total_days,
                name=name,
                status="INITIALIZED",
            )
            session.merge(run)
            session.commit()
        finally:
            session.close()

    def append_event(self, event: Event) -> None:
        """Append an immutable event to the store."""
        session: Session = self._get_session()
        try:
            model = EventModel(
                event_id=event.event_id,
                run_id=event.run_id,
                tick=event.tick,
                event_type=event.event_type,
                payload=event.payload,
            )
            session.add(model)
            session.commit()
        finally:
            session.close()

    def append_events(self, events: list[Event]) -> None:
        """Batch append multiple events in a single transaction."""
        if not events:
            return
        session: Session = self._get_session()
        try:
            models = [
                EventModel(
                    event_id=e.event_id,
                    run_id=e.run_id,
                    tick=e.tick,
                    event_type=e.event_type,
                    payload=e.payload,
                )
                for e in events
            ]
            session.add_all(models)
            session.commit()
        finally:
            session.close()

    def get_events(
        self, run_id: str, start_tick: int = 0, end_tick: int | None = None
    ) -> list[Event]:
        """Fetch chronological events for a given run and tick interval."""
        session: Session = self._get_session()
        try:
            query = session.query(EventModel).filter(
                EventModel.run_id == run_id, EventModel.tick >= start_tick
            )
            if end_tick is not None:
                query = query.filter(EventModel.tick <= end_tick)
            records = query.order_by(
                EventModel.tick.asc(), EventModel.created_at.asc()
            ).all()
            return [
                Event(
                    event_id=r.event_id,
                    run_id=r.run_id,
                    tick=r.tick,
                    event_type=r.event_type,
                    payload=r.payload,
                    created_at=r.created_at.isoformat() if r.created_at else "",
                )
                for r in records
            ]
        finally:
            session.close()

    def save_snapshot(
        self, snapshot_id: str, run_id: str, tick: int, state_blob: dict[str, Any]
    ) -> None:
        """Persist a point-in-time full state snapshot."""
        session: Session = self._get_session()
        try:
            snap = SnapshotModel(
                snapshot_id=snapshot_id,
                run_id=run_id,
                tick=tick,
                state_blob=state_blob,
            )
            session.merge(snap)
            session.commit()
        finally:
            session.close()

    def get_latest_snapshot(
        self, run_id: str, up_to_tick: int | None = None
    ) -> dict[str, Any] | None:
        """Retrieve the most recent snapshot up to a given tick."""
        session: Session = self._get_session()
        try:
            query = session.query(SnapshotModel).filter(SnapshotModel.run_id == run_id)
            if up_to_tick is not None:
                query = query.filter(SnapshotModel.tick <= up_to_tick)
            snap = query.order_by(SnapshotModel.tick.desc()).first()
            if snap:
                return {
                    "snapshot_id": snap.snapshot_id,
                    "run_id": snap.run_id,
                    "tick": snap.tick,
                    "state_blob": snap.state_blob,
                }
            return None
        finally:
            session.close()
