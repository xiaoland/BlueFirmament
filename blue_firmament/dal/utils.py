"""DAL Utils"""


import typing
from .types import QueryComLikeType, FieldLikeType
from ..utils.enum_ import dump_enum

if typing.TYPE_CHECKING:
    from .query_components import DALQueryComponent


def dump_query_coms_like(
    *values: QueryComLikeType,
    scheme_like: typing.Any | None = None
) -> typing.Iterable["DALQueryComponent"]:

    """Convert list of FilterLikeType to DALFilter list

    :param scheme_like: BaseScheme 类, BlueFirmamentField 实例

    Behavior
    --------
    - 如果 item of value 是字符串或整数，会被转换为 EqFilter
        - 使用 scheme 的主键作为字段键
    """
    res = []

    from ..scheme import BaseScheme
    from ..scheme.field import Field
    for item in values:
        if isinstance(item, (str, int)):
            try:
                if scheme_like:
                    if isinstance(scheme_like, Field):
                        scheme_like = scheme_like.scheme_cls
                    if issubclass(scheme_like, BaseScheme) or isinstance(scheme_like, BaseScheme):
                        res.append(scheme_like._get_key_field().equals(item))
                        continue

                raise ValueError
            except (AttributeError, ValueError):
                raise ValueError(
                    "Cannot dump filter-like value that is not a DALQueryComponent without scheme"
                )
        elif isinstance(item, BaseScheme):
            res.extend(item.equals())
        else:
            res.append(item)

    return typing.cast(typing.Iterable["DALQueryComponent"], res)


def dump_field_like(value: FieldLikeType) -> str:
    """Convert FieldLikeType to field name string

    :param value: to dump value
    :param dal_path: optional, Path to execute current query.
        If provided, will prepend the field name with `scheme_dal_path[0].` if
        the `dal_path` is different from the scheme's dal_path.
        (for resolving reference)
    """
    from ..scheme.field import dump_field_name
    return dump_field_name(dump_enum(value))