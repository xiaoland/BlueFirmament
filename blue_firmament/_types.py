"""Some basic types for the blue_firmament package.
"""

__all__ = [
    'AnnotatedDirective',
    'Undefined', '_undefined',
    "NamedTupleTV",
    "PathParamsT",
]

import enum
import typing


class AnnotatedDirective(enum.Enum):
    """Directive used in typing.Annotated arguments.
    """

    DNOLOG = 1
    """Do not log this value.
    """


class Undefined(enum.Enum):

    """未定义值
    """
    token = 'undefined'
_undefined: typing.Final = Undefined.token
"""未定义值全局实例"""


NamedTupleTV = typing.TypeVar("NamedTupleTV", bound=typing.NamedTuple)

type PathParamsT = typing.Dict[str, typing.Any]
"""Path parameters type.

Path parameters is the parameters resolved from TaskID path.
"""
