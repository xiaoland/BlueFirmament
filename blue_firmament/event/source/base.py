import typing
import abc
from .. import EventMetadata

if typing.TYPE_CHECKING:
    from structlog.stdlib import BoundLogger
    from ...core.app import BlueFirmamentApp


class BaseEventSource(abc.ABC):
    """The base class of the event source module (formerly event source module).
    """

    def __init__(self, app: "BlueFirmamentApp", name: str = "default") -> None:
        self._app = app
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
        return self._app._logger

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


# Backward compatibility alias
BaseEventSource = BaseEventSource

