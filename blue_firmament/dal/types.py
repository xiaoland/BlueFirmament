"""Data Access Layer Module Types
"""

import typing
from typing import Optional as Opt
import enum
if typing.TYPE_CHECKING:
    from .query_components import DALQueryComponent
    from ..model import BaseModel
    from ..model.field import Field

DALPath = typing.NewType('DALPath', typing.Tuple[str | enum.Enum | None, ...])
'''Path of DataAccessLayer

Examples
--------
>>> DALPath(('127.0.0.1:8000', 'public', 'profile'))
'''
StrictDALPath = typing.NewType('StrictDALPath', typing.Tuple[str, ...])
'''严格数据访问路径（只可以为字符串条目）'''
FieldLikeType = typing.Union[str, enum.Enum, "Field"]
'''可以作为字段的类型'''
KeyableType = typing.Union[str, int, "BaseModel"]
"""Field value type that field as a key"""
QueryComLikeType = typing.Union[KeyableType, Opt["DALQueryComponent"]]
'''Value type that can be used as query component'''
