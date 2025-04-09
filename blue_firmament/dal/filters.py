"""
Description
---
This module contains the filters for data access layer.

Author
---
- Lanzhijiang: lanzhijiang@foxmail.com

Documentation
---

"""

import enum
import typing
import abc
from ..utils import dump_enum


class DALFilter(abc.ABC):

    __filter_name__: str = ''
    
    @abc.abstractmethod
    def dump_to_sql(self) -> str:
        
        """序列化为SQL筛选语句
        """
        pass

    def dump_to_tuple(self) -> typing.Tuple[str, typing.Tuple | None]:
            
        """序列化为元组

        :returns: (筛选器名称, 筛选器参数) 筛选器参数可以是一个元组或者没有参数（``None``）
        """
        return (self.__filter_name__, None)


class EqFilter(DALFilter):

    __filter_name__ = 'eq'

    def __init__(self, field: str | enum.Enum, value: typing.Any) -> None:
        super().__init__()
        self.__field = field
        self.__value = value

    @property
    def field(self): return self.__field
    @property
    def value(self): return self.__value
    
    def dump_to_sql(self) -> str:
        return f"{self.__field} = {repr(self.__value)}"
    
    def dump_to_tuple(self) -> typing.Tuple[str, typing.Tuple[str, typing.Any]]:
        return (self.__filter_name__, (dump_enum(self.__field), self.__value))

class IsFilter(DALFilter):

    __filter_name__ = 'is'
    
    def __init__(self, field: str | enum.Enum, value: bool | None) -> None:
        super().__init__()
        self.__field = field
        self.__value = value
    
    def dump_to_sql(self) -> str:
        return f"{self.__field} IS {repr(self.__value)}"
    
    def dump_to_tuple(self) -> typing.Tuple[str, typing.Tuple[str, bool | None]]:
        return (self.__filter_name__, (dump_enum(self.__field), self.__value))

class SingleFilter(DALFilter):

    '''响应应当只有一个记录
    
    Behaviour
    ----------
    如果多于一个记录，则报错 ``DuplicateRecord``
    '''

    __filter_name__ = 'single'

    def dump_to_sql(self) -> str:
        raise NotImplementedError('SingleFilter does not support SQL dump')

    def dump_to_tuple(self) -> typing.Tuple[typing.Literal['single'], None]:
        return ("single", None)
