"""Event Context (formerly request context)
"""

__all__ = [
    "BaseEventContext", 
]

import contextvars
import typing
from typing import Optional as Opt
from ..model import BaseModel, private_field, PrivateField

if typing.TYPE_CHECKING:
    from ..log import LoggerT
    from .main import Event
    from .result import EventResult


class BaseEventContext(BaseModel):
    """Base class of EventContext (Event Context).

    .. versionchanged:: 0.1.2
        rename to BaseEventContext from RequestContext and
        removed fields from session.
    
    .. versionchanged:: 0.3.0
        Refactored to inherit from BaseModel using private fields.
    """

    _event: PrivateField["Event"] = private_field()
    _event_result: PrivateField["EventResult"] = private_field()
    _logger: PrivateField["LoggerT"] = private_field()

    __contextvar__: typing.ClassVar[contextvars.ContextVar[typing.Self]]
    __contextvar__ = contextvars.ContextVar('TASKC_CONTEXTVAR')

    def __post_init__(self) -> None:
        """Bind logger with event's trace_id after initialization."""
        self._logger = self._event.bind_logger(self._logger)

    @classmethod
    def set_contextvar(cls, task_context: typing.Self) -> None:
        cls.__contextvar__.set(task_context)
    @classmethod
    def from_contextvar(cls) -> typing.Self:
        """
        :raise LookupError: if not set
        """
        return cls.__contextvar__.get()
