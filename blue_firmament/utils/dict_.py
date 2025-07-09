"""Utils of dict
"""


import enum
import typing
from typing import Annotated as Anno
from typing import Literal as Lit
from typing import Optional as Opt
from .enum_ import dump_enum


class EnhancedDict:
    def __init__(self, parameters):
        self.__parameters: typing.Dict[str, typing.Any] = parameters

    def get(self, key: str | enum.Enum, default: typing.Any = None):
        return self.__parameters.get(dump_enum(key), default)
    
    def set(self, key: str | enum.Enum, value: typing.Any):
        self.__parameters[dump_enum(key)] = value

    def __getitem__(self, key: str | enum.Enum):
        return self.__parameters[dump_enum(key)]
