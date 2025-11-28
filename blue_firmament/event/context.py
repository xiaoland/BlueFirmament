"""Event Context (formerly request context)
"""

__all__ = [
    "BaseEventContext", 
    "SoBaseEC",
]

import contextvars
import typing
from typing import Optional as Opt
from ..model import BaseModel, private_field, Field, PrivateField

if typing.TYPE_CHECKING:
    from ..log import LoggerT
    from .main import Event
    from .result import EventResult


class BaseEventContextFields(typing.TypedDict):
    event: typing.NotRequired["Event"]
    event_result: typing.NotRequired["EventResult"]
    base_logger: typing.NotRequired["LoggerT"]
    """Bind event context based on this logger.
    """


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

    def __init__(
        self,
        btc: Opt["BaseEventContext"] = None,
        **kwargs: typing.Unpack[BaseEventContextFields]
    ):
        """
        :param btc: another BaseEventContext instance to copy from
        """
        if btc is not None:
            self.__model_init__(
                _event=btc._event,
                _event_result=btc._event_result,
                _logger=btc._logger,
            )
        else:
            event = kwargs["event"]
            logger = kwargs["base_logger"].bind(
                trace_id=event.trace_id,
            )
            self.__model_init__(
                _event=event,
                _event_result=kwargs["event_result"],
                _logger=logger,
            )

    # Keep CONTEXTVAR as class property for backward compatibility
    @property
    def CONTEXTVAR(cls) -> contextvars.ContextVar[typing.Self]:
        return cls.__contextvar__
    
    @classmethod
    def set_contextvar(cls, task_context: typing.Self) -> None:
        cls.__contextvar__.set(task_context)
    @classmethod
    def from_contextvar(cls) -> typing.Self:
        """
        :raise LookupError: if not set
        """
        return cls.__contextvar__.get()


class SoBaseEC(BaseModel):
    """Scheme attached BaseEventContext.

    By inheriting this class, your class can access
    event context and its properties with ease.

    Or by inheriting this class then override ``_event_context``'s
    type to your customized EventContext and add fields, enables
    your scheme accessing your customized event context.

    .. versionchanged:: 0.1.2
        rename to ``SoBaseEC`` from ``SchemeHasRequestContext``
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
