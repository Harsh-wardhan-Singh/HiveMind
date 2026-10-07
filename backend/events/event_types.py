"""HIVEMIND Immutable Event Types."""

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class Event:
    event_id: str
    run_id: str
    tick: int
    event_type: str
    payload: dict[str, Any]
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return asdict(self)


def create_event(
    run_id: str, tick: int, event_type: str, payload: dict[str, Any]
) -> Event:
    """Factory function for creating an immutable typed event."""
    return Event(
        event_id=f"evt_{uuid.uuid4().hex[:12]}",
        run_id=run_id,
        tick=tick,
        event_type=event_type,
        payload=payload,
    )
