# src/events.py

from typing import Callable, List, Dict

class EventBus:
    """A simple pub/sub pattern for decoupled communication."""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, callback: Callable):
        """Subscribes a callback to an event type."""
        self._subscribers.setdefault(event_type, []).append(callback)

    def publish(self, event_type: str, data: dict):
        """Publishes an event to all subscribers."""
        for callback in self._subscribers.get(event_type, []):
            callback(data)
