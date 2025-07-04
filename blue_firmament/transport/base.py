import typing
import abc
from ..task import TaskMetadata

if typing.TYPE_CHECKING:
    from ..core.app import BlueFirmamentApp


PeerInfo = typing.NewType('PeerInfo', typing.Tuple[str, int | None])


class BaseTransporter(abc.ABC):
    """The base class of the transport module.
    """

    def __init__(self, app: "BlueFirmamentApp") -> None:
        self._app = app

    @property
    def _logger(self):
        return self._app._logger

    @abc.abstractmethod
    async def start(self):
        """Start listening to tasks
        """

    @abc.abstractmethod
    async def stop(self):
        """Stop listening to tasks
        """

    @staticmethod
    def _parse_task_metadata(raw: typing.Any) -> TaskMetadata:
        if raw is None:
            return TaskMetadata()
        if isinstance(raw, dict):
            return TaskMetadata(**raw)
        raise NotImplementedError(f"Unsupported metadata parsing input type {type(raw)}")

