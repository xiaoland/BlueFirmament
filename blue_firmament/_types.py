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
    from .transport.base import BaseTransporter
    from .task import TaskRegistry


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

type TaskRegistriesT = dict["BaseTransporter" | str, "TaskRegistry"]
"""A dict, records which task registry serves which transporter.
"""

CallableTV = typing.TypeVar("CallableTV", bound=typing.Callable)
