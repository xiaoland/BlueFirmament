"""Common Task Context
"""

__all__ = [
    "CommonTaskContext",
    "SoCommonTC"
]

from blue_firmament.scheme import FieldT, private_field
from blue_firmament.task.context import SoBaseTC
from blue_firmament.session.common import CommonSession
from blue_firmament.task.context import ExtendedTaskContext


class CommonTaskContext(ExtendedTaskContext[CommonSession],
    session_cls=CommonSession
):
    """Task context extended with common session.

    .. versionadded:: 0.1.2
    """

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__()

    def _init_prop(self):
        self._daos = self._session.daos
        self._operator = self._session.operator


class SoCommonTC(SoBaseTC):

    _task_context: FieldT[CommonTaskContext] = private_field()

    @property
    def _operator(self): return self._task_context._operator
    @property
    def _daos(self): return self._task_context._daos
    @property
    def _dao(self): return self._task_context._daos(self.__class__)