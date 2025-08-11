import typing

from blue_firmament.dal.query_components import DALQueryComponent
from blue_firmament.dal.types import FieldLikeType
from blue_firmament.dal.utils import dump_field_like


class DALModifier(DALQueryComponent):
    ...


class LimitModifier(DALModifier):
    """结果只保留X个记录

    如果要限制更新、删除的记录数量，请在 update, delete 方法中使用 `limit` 参数。
    """

    def __init__(self, size: int = 1) -> None:
        super().__init__()
        self.__size = size

    def dump_to_sql(self) -> str:
        raise NotImplementedError('SingleFilter does not support SQL dump')

    def dump_to_postgrest(self) -> typing.Tuple[str, typing.Tuple[int]]:
        return ("limit", (self.__size,))

    def dump_to_postgrest_str(self) -> str:
        return f"limit.{self.__size}"


class RangeModifier(DALModifier):
    """结果只保留第X到Y个记录
    """

    def __init__(self, start: int = 0, end: int = 1) -> None:

        super().__init__()
        self.__start = start
        self.__end = end

    def dump_to_sql(self) -> str:
        raise NotImplementedError('SingleFilter does not support SQL dump')

    def dump_to_postgrest(self) -> typing.Tuple[str, typing.Tuple[int, int]]:
        return ("range", (self.__start, self.__end))

    def dump_to_postgrest_str(self) -> str:
        return f"range.{self.__start}.{self.__end}"


class OrderModifier(DALModifier):
    """按X字段排序结果
    """

    def __init__(self, field: FieldLikeType, *, desc: bool = False) -> None:
        """
        :param field: 排序字段
        :param desc: 是否降序排序（否则升序）
        """
        self._field = field
        self.__desc = desc

    def dump_to_sql(self) -> str:
        raise NotImplementedError('SingleFilter does not support SQL dump')

    def dump_to_postgrest(self) -> typing.Tuple[str, dict]:
        return ("order", {'column': dump_field_like(self._field), 'desc': self.__desc})

    def dump_to_postgrest_str(self) -> str:
        order_type = 'desc' if self.__desc else 'asc'
        return f"{dump_field_like(self._field)}.order.{order_type}"
