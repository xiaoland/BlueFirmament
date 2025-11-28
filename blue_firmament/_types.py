"""Some basic types for the blue_firmament package.
"""

__all__ = [
    'AnnotatedDirective',
    'Undefined', '_undefined',
    "NamedTupleTV",
    "PathParamsT",
    "EventRegistriesT",
    "EventBusesT",
    "CallableTV",
]

import enum
import typing

if typing.TYPE_CHECKING:
    from .event.source.base import BaseEventSource
    from .event import EventBus
    # Backward compatibility alias
    EventRegistry = EventBus


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

Path parameters is the parameters resolved from EventID path.
"""

type EventBusesT = dict["BaseEventSource" | str, "EventBus"]
"""A dict, records which event bus serves which event source.
"""

# Backward compatibility alias
type EventRegistriesT = EventBusesT
"""Backward compatibility alias for EventBusesT.
"""

CallableTV = typing.TypeVar("CallableTV", bound=typing.Callable)
