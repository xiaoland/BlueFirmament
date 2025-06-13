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

from .utils import dump_field_like
from .types import FieldLikeType


class DALFilter(abc.ABC):

    __filter_name__: str = ''
    
    @abc.abstractmethod
    def dump_to_sql(self) -> str:
        
        """序列化为SQL筛选语句
        """
        pass

    def dump_to_tuple(self) -> typing.Tuple[
        str, typing.Tuple | typing.Dict | None
    ]:
            
        """序列化为元组

        :returns: (筛选器名称, 筛选器参数) 

            筛选器参数：
            - 是元组则为作为位置参数传入
            - 是字典则为作为关键字参数传入
            - 没有参数为``None``
        """
        return (self.__filter_name__, None)
    
    def __repr__(self):
        return f"{self.__class__.__name__}:"


class HasField:

    def __init__(self, field: FieldLikeType) -> None:
        self.__field = field

    @property
    def field(self): 
        return dump_field_like(self.__field)
    
    def __repr__(self):
        return super().__repr__() + f'field={self.__field},'
    
class HasValue:

    """
    特性
    ----
    自动转换
    ^^^^^^^^
    > to primitive python types 
    TODO 使用 to_primitive() 方法 ? 还是 converter.dump() ?

    - enum.Enum -> enum.Enum.value
    """

    def __init__(self, value: typing.Any) -> None:
        self.__value = value

    @property
    def value(self):
        if isinstance(self.__value, enum.Enum):
            return self.__value.value
        return self.__value
    
    def __repr__(self):
        return super().__repr__() + f'value={self.__value},'


class EqFilter(HasField, HasValue, DALFilter):

    __filter_name__ = 'eq'

    def __init__(self, field: FieldLikeType, value: typing.Any) -> None:
        
        HasField.__init__(self, field)
        HasValue.__init__(self, value)
    
    def dump_to_sql(self) -> str:
        return f"{self.field} = {repr(self.value)}"
    
    def dump_to_tuple(self):
        return (self.__filter_name__, (self.field, self.value))

class NotEqFilter(HasField, HasValue, DALFilter):

    __filter_name__ = 'neq'
    
    def __init__(self, field: FieldLikeType, value: typing.Any) -> None:
        
        HasField.__init__(self, field)
        HasValue.__init__(self, value)
    
    def dump_to_sql(self) -> str:
        return f"{self.field} != {repr(self.value)}"
    
    def dump_to_tuple(self):
        return (self.__filter_name__, (self.field, self.value))

class IsFilter(HasField, HasValue, DALFilter):

    __filter_name__ = 'is_'
    
    def __init__(self, field: FieldLikeType, value: bool | None) -> None:
        
        HasField.__init__(self, field)
        HasValue.__init__(self, value)
    
    def dump_to_sql(self) -> str:
        return f"{self.field} IS {repr(self.value)}"
    
    def dump_to_tuple(self):
        return (self.__filter_name__, (self.field, self.value))

class NotFilter(DALFilter):

    __filter_name__ = 'not_'

    def dump_to_sql(self) -> str:
        return "NOT"

    def dump_to_tuple(self) -> typing.Tuple[str, tuple]:
        return (self.__filter_name__, ())

class InFilter(HasField, HasValue, DALFilter):

    __filter_name__ = 'in_'
    
    def __init__(self, field: FieldLikeType, value: typing.Iterable[typing.Any]) -> None:
        
        HasField.__init__(self, field)
        HasValue.__init__(self, value)
    
    def dump_to_sql(self) -> str:
        return f"{self.field} IN ({', '.join(repr(v) for v in self.value)})"
    
    def dump_to_tuple(self):
        return (self.__filter_name__, (self.field, self.value))
    
class ContainsFilter(HasField, HasValue, DALFilter):

    __filter_name__ = 'contains'
    
    def __init__(self, field: FieldLikeType, /, *value: typing.Any) -> None:
        
        HasField.__init__(self, field)
        HasValue.__init__(self, value)
    
    def dump_to_sql(self) -> str:
        return f"{self.field} LIKE {repr('%' + self.value + '%')}"
    
    def dump_to_tuple(self):
        return (self.__filter_name__, (self.field, self.value))


class LimitModifier(DALFilter):  # TODO DALModifier

    '''结果只保留X个记录
    '''

    __filter_name__ = 'limit'
    
    def __init__(self, size: int = 1) -> None:
        
        super().__init__()
        self.__size = size

    def dump_to_sql(self) -> str:
        raise NotImplementedError('SingleFilter does not support SQL dump')

    def dump_to_tuple(self) -> typing.Tuple[str, typing.Tuple[int]]:
        return ("limit", (self.__size,))
    

class RangeModifier(DALFilter):  # TODO DALModifier

    '''结果只保留第X到Y个记录
    '''

    __filter_name__ = 'range'
    
    def __init__(self, start: int = 0, end: int = 1) -> None:
        
        super().__init__()
        self.__start = start
        self.__end = end

    def dump_to_sql(self) -> str:
        raise NotImplementedError('SingleFilter does not support SQL dump')

    def dump_to_tuple(self) -> typing.Tuple[str, typing.Tuple[int, int]]:
        return ("range", (self.__start, self.__end))


class OrderModifier(DALFilter):  # TODO DALModifier

    '''按X字段排序结果
    '''

    __filter_name__ = 'order'
    
    def __init__(self, field: FieldLikeType, *, desc: bool = False) -> None:

        """
        :param field: 排序字段
        :param desc: 是否降序排序（否则升序）
        """
        
        super().__init__()
        self.__field = field
        self.__desc = desc

    def dump_to_sql(self) -> str:
        raise NotImplementedError('SingleFilter does not support SQL dump')

    def dump_to_tuple(self) -> typing.Tuple[str, dict]:
        return ("order", {'column': self.__field, 'desc': self.__desc})