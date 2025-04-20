'''Exceptions of BlueFirmament DAL Module'''

import typing
from typing import Optional as Opt

if typing.TYPE_CHECKING:
    from .base import DataAccessObject
    from .filters import DALFilter
    from . import DALPath


class DALException(Exception):
    '''Base Exception for DAL'''

    def __init__(self, 
        path: Opt["DALPath"],
        dao: Opt["DataAccessObject"] = None,
    ) -> None:
        super().__init__()

        self._path = path
        self._dao = dao
    
    def __str__(self) -> str:
        return f'{self.__class__.__name__}: '


class TooManyRecords(DALException):
    
    '''太多记录
    
    场景
    ^^^^^^
    - 要求获得不超过指定数量的记录，但结果超过该值
    '''
    
    def __init__(self, actual: int, limit: int = 1,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)

        self._actual: int = actual
        self._limit: int = limit

    def __str__(self) -> str:
        return super().__str__() + f'expect {self._limit} records, but got {self._actual}'


class NotFound(DALException):

    '''未找到记录
    '''

    def __init__(self, 
        path: Opt["DALPath"], dao: Opt["DataAccessObject"] = None,
        filters: typing.Iterable["DALFilter"] = ()
    ) -> None:
        
        super().__init__(path, dao)
        self._filters = filters

    def __str__(self) -> str:
        return super().__str__() + f'no records found in {self._path} where {self._filters}'


class UpdateFailure(DALException):

    '''更新失败
    
    场景
    ^^^^^^
    - RLS 导致的更新失败
    '''
