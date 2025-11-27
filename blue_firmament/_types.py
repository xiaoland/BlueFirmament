"""Some basic types for the blue_firmament package.
"""

__all__ = [
    'AnnotatedDirective',
    'Undefined', '_undefined',
    "NamedTupleTV",
    "PathParamsT",
    "TaskRegistriesT",
    "CallableTV",
]

import enum
import typing

if typing.TYPE_CHECKING:
    from .event.source.base import BaseEventSource
    from .event import TaskRegistry
    # Backward compatibility alias
    BaseTransporter = BaseEventSource


class AnnotatedDirective(enum.Enum):
    """Directive used in typing.Annotated arguments.
    """
    NOLOG = 1
    """Don't log this value.
    """


class Undefined(enum.Enum):
    token = 'undefined'
_undefined: typing.Final = Undefined.token

NamedTupleTV = typing.TypeVar("NamedTupleTV", bound=typing.NamedTuple)

type PathParamsT = typing.Dict[str, typing.Any]
"""Path parameters type.

Path parameters is the parameters resolved from TaskID path.
"""

type TaskRegistriesT = dict["BaseEventSource" | str, "TaskRegistry"]
"""A dict, records which task registry serves which event source.
"""

CallableTV = typing.TypeVar("CallableTV", bound=typing.Callable)
