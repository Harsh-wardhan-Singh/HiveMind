"""HIVEMIND In-Memory Synchronous Event Bus."""

from collections.abc import Callable

from backend.events.event_types import Event


class EventBus:
    """Synchronous in-memory event dispatcher for decoupled event subscribers."""

    def __init__(self):
        self._subscribers: dict[str, list[Callable[[Event], None]]] = {}
        self._wildcard_subscribers: list[Callable[[Event], None]] = []

    def subscribe(self, event_type: str, handler: Callable[[Event], None]) -> None:
        """Register a handler for a specific event type."""
        if event_type == "*":
            self._wildcard_subscribers.append(handler)
        else:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(handler)

    def publish(self, event: Event) -> None:
        """Dispatch event to registered handlers."""
        # Specific handlers
        if event.event_type in self._subscribers:
            for handler in self._subscribers[event.event_type]:
                handler(event)
        # Wildcard handlers
        for handler in self._wildcard_subscribers:
            handler(event)

    def clear(self) -> None:
        """Clear all subscribers."""
        self._subscribers.clear()
        self._wildcard_subscribers.clear()
