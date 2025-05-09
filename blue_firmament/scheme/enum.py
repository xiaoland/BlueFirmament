"""枚举数据模型
"""

import enum
import typing
from typing import Optional as Opt, Annotated as Anno, Literal as Lit

from ..exceptions import InvalidStatusTransition


EnumClassTV = typing.TypeVar('EnumClassTV', bound=typing.Type[enum.Enum])
"""枚举类类型变量"""
EnumMemberTV = typing.TypeVar('EnumMemberTV', bound=enum.Enum)
"""枚举成员类型变量

也就是枚举实例
"""

class Status(enum.Enum):

    """状态

    Examples
    --------
    .. code-block:: python
        from blue_firmament.scheme.enum import Status

        class MyStatus(Status):

            OPEN = "open"
            CLOSED = "closed"
            CANCELLED = "cancelled"

            def to_cancelled(self) -> typing.Literal["MyStatus.CANCELLED"]:
                return self.to_target_status(MyStatus.CANCELLED, 
                    MyStatus.OPEN  # break a line here to disguish allowed_from from target
                )

        MyStatus.CLOSED.to_cancelled()  
        # raise InvalidStatusTransition
        MyStatus.OPEN.to_cancelled() 
        # return MyStatus.CANCELLED
    """

    def _to_target_status(self, 
        target: EnumMemberTV,
        *allowed_from: "Status",
    ) -> EnumMemberTV:
        
        """转换到目标状态

        :param target: 目标状态
        :raises InvalidStatusTransition: 如果当前状态不处于 `allowed_from` 中 
        :return: 目标状态
        """
        if self not in allowed_from:
            raise InvalidStatusTransition.from_enum_member(self, target)
        return target
