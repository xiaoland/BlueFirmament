"""BlueFirmament Event Source.

Event sources emit events to an event bus. They abstract the origin
of events (e.g., external systems, user actions, scheduled tasks).
"""

__all__ = [
    "EventSource",
]

import typing
from typing import Optional as Opt

from .model import Event, EventID
from .bus import EventBus
from ..log import get_logger

if typing.TYPE_CHECKING:
    from structlog.stdlib import BoundLogger


LOGGER = get_logger(__name__)


class EventSource:
    """Base class for event sources.

    Event sources emit events directly to an event bus.
    Subclasses can implement specific event source behaviors
    (e.g., message queue listeners, webhook handlers).

    Example:
        ```python
        bus = EventBus()
        source = EventSource(bus, name="user_service")

        # Emit an event
        await source.emit("user.created", {"user_id": 123})
        ```
    """

    def __init__(
        self,
        event_bus: EventBus,
        name: str = "default",
    ):
        """Initialize the event source.

        Args:
            event_bus: The event bus to emit events to
            name: Name of this event source
        """
        self._event_bus = event_bus
        self._name = name
        self._logger: "BoundLogger" = LOGGER.bind(
            event_source=name,
            event_bus=event_bus.name,
        )

    @property
    def name(self) -> str:
        """Name of this event source."""
        return self._name

    @property
    def event_bus(self) -> EventBus:
        """The event bus this source emits to."""
        return self._event_bus

    async def emit(
        self,
        path: str,
        parameters: Opt[dict[str, typing.Any]] = None,
        metadata: Opt[dict[str, typing.Any]] = None,
        separator: str = ".",
        context: typing.Optional[typing.Any] = None,
    ) -> Event:
        """Emit an event to the event bus.

        Args:
            path: Event path (e.g., 'user.created')
            parameters: Event data
            metadata: Additional metadata
            separator: Path separator
            context: Optional context for middlewares/handlers

        Returns:
            The emitted event
        """
        # Add source info to metadata
        event_metadata = metadata or {}
        event_metadata["source"] = self._name

        event = Event.create(
            path=path,
            parameters=parameters,
            metadata=event_metadata,
            separator=separator,
        )

        self._logger.info(
            "Emitting event",
            event_id=str(event.id),
            trace_id=event.trace_id,
        )

        await self._event_bus.emit(event, context=context)

        return event

    async def emit_event(
        self,
        event: Event,
        context: typing.Optional[typing.Any] = None,
    ) -> None:
        """Emit a pre-constructed event to the event bus.

        Args:
            event: The event to emit
            context: Optional context for middlewares/handlers

        Note:
            Source info is logged but not added to event metadata
            to avoid mutating the original event.
        """
        self._logger.info(
            "Emitting event",
            event_id=str(event.id),
            trace_id=event.trace_id,
            source=self._name,
        )

        await self._event_bus.emit(event, context=context)
