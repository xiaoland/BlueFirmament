"""Data Access Layer Module Types
"""

import typing
import enum
if typing.TYPE_CHECKING:
    from .filters import DALFilter
    from ..scheme.field import Field
    from ..scheme import BaseScheme


DALPath = typing.NewType('DALPath', typing.Tuple[str | enum.Enum | None, ...])
'''Path of DataAccessLayer

Examples
--------
>>> DALPath(('127.0.0.1:8000', 'public', 'profile'))
'''
StrictDALPath = typing.NewType('StrictDALPath', typing.Tuple[str, ...])
'''严格数据访问路径（只可以为字符串条目）'''
type FieldLikeType = typing.Union[str, enum.Enum, "Field"]
'''可以作为字段的类型'''
type KeyableType = typing.Union[str, int, "BaseScheme"]
"""Field value type that field as a key"""
type FilterLikeType = typing.Union[KeyableType, "DALFilter"]
'''Value type that can be used as filter'''
