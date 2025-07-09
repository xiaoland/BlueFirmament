import typing
import abc
from ..task import TaskMetadata

if typing.TYPE_CHECKING:
    from structlog.stdlib import BoundLogger
    from ..core.app import BlueFirmamentApp


class BaseTransporter(abc.ABC):
    """The base class of the transport module.
    """

    def __init__(self, app: "BlueFirmamentApp", name: str = "default") -> None:
        self._app = app
        self._name = name

    def __hash__(self):
        return hash(self._name)

    def __eq__(self, other):
        if isinstance(other, str):
            return self._name == other
        if isinstance(other, BaseTransporter):
            return self._name == other._name
        return False

    def __str__(self):
        return self._name

    @property
    def name(self) -> str:
        """ID of the transporter.
        """
        return self._name

    @property
    def _logger(self) -> "BoundLogger":
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

