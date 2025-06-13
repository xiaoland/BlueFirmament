"""枚举数据模型
"""

import enum
import typing
from typing import Optional as Opt, Annotated as Anno, Literal as Lit

from ..exceptions import InvalidStatusTransition


EnumClassTV = typing.TypeVar('EnumClassTV', bound=typing.Type[enum.Enum])
"""TypeVar of Enum class"""
EnumMemberTV = typing.TypeVar('EnumMemberTV', bound=enum.Enum)
"""TypeVar of Enum memebr(instance)
"""

@enum.unique
class Status(enum.Enum):

    """
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
        
        """Return target status if allowed (Idempotent)

        :param target: 
        :param allowed_from: 
            Allowed source status to go to the target status
        :raises InvalidStatusTransition: 
            When current status is not in `allowed_from`.
            Not include case that is already at target status.
        :return: The target status
        """
        if self is not target:
            if self not in allowed_from:
                raise InvalidStatusTransition.from_enum_member(self, target)
        return target
