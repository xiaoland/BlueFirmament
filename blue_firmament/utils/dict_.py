"""Utils of dict"""

import enum
import typing
from typing import Annotated as Anno
from typing import Literal as Lit
from typing import Optional as Opt
from .enum_ import dump_enum


def get_nested_value(
    data: typing.Dict[str, typing.Any], key: str, separator: str = "."
) -> typing.Any:
    """Get a value from a nested dictionary using dot notation.

    Parameters
    ----------
    data : Dict[str, Any]
        The dictionary to search in.
    key : str
        The key path using dot notation (e.g., "database.host").
    separator : str
        The separator used in the key path. Default is ".".

    Returns
    -------
    Any
        The value at the key path, or None if not found.

    Example
    -------
    >>> data = {"database": {"host": "localhost", "port": 5432}}
    >>> get_nested_value(data, "database.host")
    'localhost'
    >>> get_nested_value(data, "database.port")
    5432
    >>> get_nested_value(data, "database.user")
    None
    """
    keys = key.split(separator)
    value = data

    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return None

    return value


class EnhancedDict:
    def __init__(self, parameters):
        self.__parameters: typing.Dict[str, typing.Any] = parameters

    def get(self, key: str | enum.Enum, default: typing.Any = None):
        return self.__parameters.get(dump_enum(key), default)

    def set(self, key: str | enum.Enum, value: typing.Any):
        self.__parameters[dump_enum(key)] = value

    def __getitem__(self, key: str | enum.Enum):
        return self.__parameters[dump_enum(key)]
