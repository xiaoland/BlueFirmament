import typing
import abc
from .. import EventMetadata

if typing.TYPE_CHECKING:
    from structlog.stdlib import BoundLogger
    from ..bus import EventBus


class BaseEventSource(abc.ABC):
    """The base class of the event source module.

    Event sources receive events from external systems and dispatch them
    to the event bus for handling.
    """

    def __init__(self, event_bus: "EventBus", name: str = "default") -> None:
        """
        :param event_bus: The event bus to dispatch events to
        :param name: Name identifier for this event source
        """
        self._event_bus = event_bus
        self._name = name

    def __hash__(self):
        return hash(self._name)

    def __eq__(self, other):
        if isinstance(other, str):
            return self._name == other
        if isinstance(other, BaseEventSource):
            return self._name == other._name
        return False

    def __str__(self):
        return self._name

    @property
    def name(self) -> str:
        """ID of the event source.
        """
        return self._name

    @property
    def _logger(self) -> "BoundLogger":
        return self._event_bus._logger

    @abc.abstractmethod
    async def start(self):
        """Start listening to events
        """

    @abc.abstractmethod
    async def stop(self):
        """Stop listening to events
        """

    @staticmethod
    def _parse_event_metadata(raw: typing.Any) -> EventMetadata:
        if raw is None:
            return EventMetadata()
        if isinstance(raw, dict):
            return EventMetadata(**raw)
        raise NotImplementedError(f"Unsupported metadata parsing input type {type(raw)}")

