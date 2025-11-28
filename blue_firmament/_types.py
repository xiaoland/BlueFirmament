"""Some basic types for the blue_firmament package.
"""

__all__ = [
    'AnnotatedDirective',
    'Undefined', '_undefined',
    "NamedTupleTV",
    "PathParamsT",
    "CallableTV",
]

import enum
import typing


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

CallableTV = typing.TypeVar("CallableTV", bound=typing.Callable)
