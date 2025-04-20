"""Data Access Layer (DAL) of Blue Firmament"""

import typing
import enum
from ..utils import dump_enum
if typing.TYPE_CHECKING:
    from ..scheme.field import BlueFirmamentField
    from ..scheme import BaseScheme
    from .filters import DALFilter


DALPath = typing.NewType('DALPath', typing.Tuple[str | enum.Enum | None, ...])
'''数据访问路径'''
StrictDALPath = typing.NewType('StrictDALPath', typing.Tuple[str, ...])
'''严格数据访问路径（只可以为字符串条目）'''
type FieldLikeType = typing.Union[str, enum.Enum, "BlueFirmamentField"]
'''可以作为字段的类型'''
type FilterLikeType = typing.Union[str, int, "DALFilter"]
'''可以作为筛选器的类型'''



def dump_field_like(value: FieldLikeType) -> str:
    from ..scheme.field import dump_field_name
    return dump_field_name(dump_enum(value))

def dump_filters_like(
    *value: FilterLikeType,
    scheme: typing.Any | None = None
) -> typing.Iterable["DALFilter"]:
    
    """
    将 FilterLikeType 的列表序列化为 DALFilter 列表

    :param scheme: BaseScheme 类, BlueFirmamentField 实例

    Behavior
    --------
    - 如果 item of value 是字符串或整数，会被转换为 EqFilter
        - 使用 scheme 的主键作为字段键
    """
    res = []
    
    for item in value:
        if isinstance(item, (str, int)):
            try:
                if scheme:
                    from .filters import EqFilter

                    from ..scheme.field import BlueFirmamentField
                    if isinstance(scheme, BlueFirmamentField):
                        scheme = scheme.scheme_cls
                    
                    res.append(EqFilter(
                        scheme.get_primary_key(),
                        item
                    ))
                else:
                    raise ValueError
            except (AttributeError, ValueError):
                raise ValueError(
                    "Cannot dump filter-like value that is not a DALFilter without scheme"
                )
        else:
            res.append(item)

    return typing.cast(typing.Iterable["DALFilter"], res)
