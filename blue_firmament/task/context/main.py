"""请求上下文
"""

__all__ = [
    "BaseTaskContext", 
    "ExtendedTaskContext",
    "SoBaseTC",
]

import contextvars
import typing
from typing import Optional as Opt
from blue_firmament.session import SessionTV
from blue_firmament.scheme.main import SchemeTV
from blue_firmament.scheme import BaseScheme, private_field, FieldT

if typing.TYPE_CHECKING:
    from blue_firmament.log import LoggerT
    from blue_firmament.task import Task
    from blue_firmament.task.result import TaskResult


class BaseTaskContextFields(typing.TypedDict):
    task: typing.NotRequired["Task"]
    task_result: typing.NotRequired["TaskResult"]
    base_logger: typing.NotRequired["LoggerT"]
    """Bind task context based on this logger.
    """


class BaseTaskContext:
    """Base class of TaskContext.

    .. versionchanged:: 0.1.2
        rename to BaseTaskContext from RequestContext and
        removed properties from session.
    """

    def __init__(self,
        btc: Opt["BaseTaskContext"] = None,
        **kwargs: typing.Unpack[BaseTaskContextFields]
    ):
        """
        :param btc: another BaseTaskContext instance to copy from
        """
        if btc:
            self.__task = btc._task
            self.__task_result = btc._task_result
            self.__logger = btc._logger
        else:
            self.__task = kwargs["task"]
            self.__task_result = kwargs["task_result"]
            self.__logger = kwargs["base_logger"].bind(
                trace_id=self.__task.trace_id,
            )
    @property
    def _task(self) -> "Task": return self.__task
    @property
    def _task_result(self) -> 'TaskResult': return self.__task_result
    @property
    def _logger(self) -> "LoggerT": return self.__logger
    @_logger.setter
    def _logger(self, new_logger: "LoggerT"): self.__logger = new_logger
    
    CONTEXTVAR = contextvars.ContextVar[typing.Self]('TASKC_CONTEXTVAR')
    @classmethod
    def set_contextvar(cls, task_context: typing.Self) -> None:
        cls.CONTEXTVAR.set(task_context)
    @classmethod
    def from_contextvar(cls) -> typing.Self:
        """
        :raise LookupError: if not set
        """
        return cls.CONTEXTVAR.get()

    @classmethod
    def try_from_scheme_and_convar(cls, scheme_ins: Opt[SchemeTV] = None) -> "BaseTaskContext":

        """
        尝试从上下文变量或者包含请求上下文的数据模型中获取请求上下文

        .. deprecated:: bad name and unclear usecase

        :param scheme_ins: 
            包含请求上下文的数据模型
            
            优先级最高
        :raise LookupError: 都失败
        """
        if scheme_ins is not None:
            if isinstance(scheme_ins, SoBaseTC):
                return scheme_ins._task_context
        return cls.from_contextvar()


class ExtendedTaskContext(
    typing.Generic[SessionTV],
    BaseTaskContext, 
):
    """Extend BaseTaskContext with session.
    """

    def __init_subclass__(cls, 
        session_cls: Opt[typing.Type[SessionTV]] = None
    ) -> None:
        if session_cls:
            cls.__session_cls = session_cls
        super().__init_subclass__()

    def __init__(self, btc: BaseTaskContext):
        super().__init__(btc=btc)
        self.__session = self.__session_cls.from_task(btc._task)
        self._init_prop()
    def _init_prop(self): 
        """Assign your customized properties"""
        pass
    @property
    def _session(self): return self.__session


class SoBaseTC(BaseScheme):
    """Scheme attached BaseTaskContext.

    By inheriting this class, your class can access
    task context and its properties with ease.

    Or by inheriting this class then override ``_task_context``'s
    type to your customized TaskContext and add properties, you enables
    your scheme accessing your customized task context.

    .. versionchanged:: 0.1.2
        rename to ``SoBTC`` from ``SchemeHasRequestContext``
    """

    _task_context: FieldT[BaseTaskContext] = private_field(
        default_factory=BaseTaskContext.from_contextvar
    )

    def __post_init__(self) -> None:
        # update scheme logger context
        self._set_logger(self._logger.bind(
            **self._task_context._logger._context
        ))

    @property
    def _task(self):
        return self._task_context._task
    @property
    def _task_result(self):
        return self._task_context._task_result
