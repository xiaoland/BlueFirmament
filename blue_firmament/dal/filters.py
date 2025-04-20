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

from . import FieldLikeType, dump_field_like


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


class HasField:

    def __init__(self, field: FieldLikeType) -> None:
        self.__field = field

    @property
    def field(self): 
        return dump_field_like(self.__field)
    
class HasValue:

    def __init__(self, value: typing.Any) -> None:
        self.__value = value

    @property
    def value(self):
        return self.__value


class EqFilter(DALFilter, HasField, HasValue):

    __filter_name__ = 'eq'

    def __init__(self, field: FieldLikeType, value: typing.Any) -> None:
        
        HasField.__init__(self, field)
        HasValue.__init__(self, value)
    
    def dump_to_sql(self) -> str:
        return f"{self.field} = {repr(self.value)}"
    
    def dump_to_tuple(self):
        return (self.__filter_name__, (self.field, self.value))

class IsFilter(DALFilter, HasField, HasValue):

    __filter_name__ = 'is_'
    
    def __init__(self, field: FieldLikeType, value: bool | None) -> None:
        
        HasField.__init__(self, field)
        HasValue.__init__(self, value)
    
    def dump_to_sql(self) -> str:
        return f"{self.field} IS {repr(self.value)}"
    
    def dump_to_tuple(self):
        return (self.__filter_name__, (self.field, self.value))

class LimitFilter(DALFilter):

    '''响应应当只有X个记录
    
    Behaviour
    ----------
    如果多于X记录，则报错 ``?``
    '''

    __filter_name__ = 'limit'
    
    def __init__(self, size: int = 1) -> None:
        
        super().__init__()
        self.__size = size

    def dump_to_sql(self) -> str:
        raise NotImplementedError('SingleFilter does not support SQL dump')

    def dump_to_tuple(self) -> typing.Tuple[str, typing.Tuple[int]]:
        return ("limit", (self.__size,))
