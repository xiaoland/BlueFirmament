"""Common Event Context (formerly Common Task Context)
"""

__all__ = [
    "CommonEventContext",
    "SoCommonEC"
]

import typing
from ... import event
from ...model import Field, private_field
from . import SoBaseEC, ExtendedEventContext
from ...session.common import CommonSession
if typing.TYPE_CHECKING:
    from ...dal import DataAccessObjects


class CommonEventContext(
    ExtendedEventContext[CommonSession],
    session_cls=CommonSession
):
    """Event context extended with common session.

    .. versionadded:: 0.1.2
    """

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__()

    @property
    def _emit(self):
        return event.simple_emit
    @property
    def _daos(self):
        return self._session.daos
    @property
    def _operator(self):
        return self._session.operator


class SoCommonEC(SoBaseEC):
    """Scheme of CommonEventContext"""

    _task_context: Field[CommonEventContext] = private_field(
        default_factory=CommonEventContext.from_contextvar
    )

    @property
    def _operator(self): return self._task_context._operator
    @property
    def _daos(self): return self._task_context._daos
    @property
    def _dao(self): return self._task_context._daos(self.__class__)