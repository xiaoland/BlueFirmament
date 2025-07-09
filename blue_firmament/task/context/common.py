"""Common Task Context
"""

__all__ = [
    "CommonTaskContext",
    "SoCommonTC"
]

from ... import event
from ...scheme import FieldT, private_field
from ..context import SoBaseTC, ExtendedTaskContext
from ...session.common import CommonSession


class CommonTaskContext(
    ExtendedTaskContext[CommonSession],
    session_cls=CommonSession
):
    """Task context extended with common session.

    .. versionadded:: 0.1.2
    """

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__()

    def __init_fields__(self):
        self._daos = self._session.daos
        self._operator = self._session.operator

    @property
    def _emit(self):
        return event.simple_emit


class SoCommonTC(SoBaseTC):

    _task_context: FieldT[CommonTaskContext] = private_field(
        default_factory=CommonTaskContext.from_contextvar
    )

    @property
    def _operator(self): return self._task_context._operator
    @property
    def _daos(self): return self._task_context._daos
    @property
    def _dao(self): return self._task_context._daos(self.__class__)