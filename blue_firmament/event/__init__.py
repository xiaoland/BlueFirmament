"""BlueFirmament Event System.

The event module provides:
- Event: Data model for events (based on BaseScheme)
- EventBus: Central hub for event handlers and middleware
- EventSource: Emits events to the event bus
- Middleware: Intercepts events before handlers

Example:
    ```python
    from blue_firmament.event import Event, EventBus, EventSource

    # Create event bus
    bus = EventBus()

    # Register handler
    @bus.on(r"user\\..*")
    async def handle_user_events(event: Event):
        print(f"User event: {event.id}")

    # Create event source
    source = EventSource(bus, name="user_service")

    # Emit events
    await source.emit("user.created", {"user_id": 123})
    ```
"""

__all__ = [
    # Model
    "Event",
    "EventID",
    # Bus
    "EventBus",
    "EventHandler",
    "on_event",
    # Middleware
    "BaseMiddleware",
    "MiddlewaresT",
    "NextT",
    # Source
    "EventSource",
]

from .model import Event, EventID
from .bus import EventBus, EventHandler, on_event
from .middleware import BaseMiddleware, MiddlewaresT, NextT
from .source import EventSource
