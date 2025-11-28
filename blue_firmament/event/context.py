"""Event Context (formerly request context)
"""

__all__ = [
    "BaseEventContext", 
    "SoBaseEC",
]

import contextvars
import typing
from typing import Optional as Opt
from ..model import BaseModel, private_field, Field

if typing.TYPE_CHECKING:
    from ..log import LoggerT
    from .main import Event
    from .result import EventResult


class BaseEventContextFields(typing.TypedDict):
    event: typing.NotRequired["Event"]
    event_result: typing.NotRequired["EventResult"]
    base_logger: typing.NotRequired["LoggerT"]
    """Bind task context based on this logger.
    """


class BaseEventContext:
    """Base class of EventContext (Event Context).

    .. versionchanged:: 0.1.2
        rename to BaseEventContext from RequestContext and
        removed fields from session.
    """

    def __init__(
        self,
        btc: Opt["BaseEventContext"] = None,
        **kwargs: typing.Unpack[BaseEventContextFields]
    ):
        """
        :param btc: another BaseEventContext instance to copy from
        """
        if btc:
            self.__event = btc._event
            self.__event_result = btc._event_result
            self.__logger = btc._logger
        else:
            self.__event = kwargs["event"]
            self.__event_result = kwargs["event_result"]
            self.__logger = kwargs["base_logger"].bind(
                trace_id=self.__event.trace_id,
            )

    @property
    def _event(self) -> "Event": return self.__event
    @property
    def _event_result(self) -> 'EventResult': return self.__event_result
    @property
    def _logger(self) -> "LoggerT": return self.__logger
    @_logger.setter
    def _logger(self, new_logger: "LoggerT"): self.__logger = new_logger
    
    CONTEXTVAR = contextvars.ContextVar[typing.Self]('TASKC_CONTEXTVAR')
    @classmethod
    def set_contextvar(cls, task_context: typing.Self) -> None:
        cls.CONTEXTVAR.set(task_context)
    @classmethod
    def from_contextvar(cls) -> typing.Self:
        """
        :raise LookupError: if not set
        """
        return cls.CONTEXTVAR.get()


class SoBaseEC(BaseModel):
    """Scheme attached BaseEventContext.

    By inheriting this class, your class can access
    task context and its properties with ease.

    Or by inheriting this class then override ``_event_context``'s
    type to your customized EventContext and add fields, enables
    your scheme accessing your customized task context.

    .. versionchanged:: 0.1.2
        rename to ``SoBTC`` from ``SchemeHasRequestContext``
    """

    _event_context: Field[BaseEventContext] = private_field(
        default_factory=BaseEventContext.from_contextvar
    )

    def __post_init__(self) -> None:
        # update scheme logger context
        self._set_logger(self._logger.bind(
            **self._event_context._logger._context
        ))

    @property
    def _event(self):
        return self._event_context._event
    @property
    def _event_result(self):
        return self._event_context._event_result
