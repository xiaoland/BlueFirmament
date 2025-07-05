"""Task handler module.
"""

import inspect
import typing
from typing import Optional as Opt

from .._types import PathParamsT, _undefined
from ..exceptions import InternalError
from ..scheme import BaseConverter
from ..scheme.converter import get_converter_from_anno
from . import Task
from .result import TaskResult, Body, EmptyBody, JsonBody
from ..utils import call_as_async
from ..utils.type import get_origin, safe_issubclass, is_json_dumpable

if typing.TYPE_CHECKING:
    from .main import BaseTaskContext
    from ..manager import BaseManager


class TaskHandler:
    """BlueFirmament TaskHandler

    Automatically resolve parameters that inner handler (function) needed from
    TaskContext.
    """

    type FunctionKwargsT = typing.Dict[
        str,
        typing.Callable[
            ["BaseTaskContext", PathParamsT], typing.Coroutine,
        ]
    ]
    """Inner handler parameters"""
    type FunctionT = typing.Union[
        typing.Callable[..., typing.Any],
        typing.Callable[..., typing.Awaitable[typing.Any]]
    ]

    def __init__(
        self,
        function: FunctionT,
        manager_cls: Opt[typing.Type["BaseManager"]] = None,
    ):
        """
        :param function:
        :param manager_cls:
            When the inner_handler is a manager method
            (excludes classmethod, staticmethod).
        """
        self.__function = function
        self.__method_manager_cls = manager_cls

        # parse handler kwargs
        self.__handler_kwargs: TaskHandler.FunctionKwargsT =\
            self._parse_handler_kwargs(self.__function)

    @property
    def function(self) -> FunctionT:
        return self.__function

    def set_manager_cls(self, manager_cls: typing.Type["BaseManager"]):
        """Set inner handler's manager class if it's a manager method.

        Useful for manager class created after task handler created.
        E.g. use :meth:`blue_firmament.task.task` to decorate a manager method.
        """
        self.__method_manager_cls = manager_cls

    @staticmethod
    def get_param_getter(name: str, converter: BaseConverter):
        """Get a getter resolves parameter from
        task parameters or path parameters.
        """
        async def getter(tc: "BaseTaskContext", path_params: PathParamsT):
            val = path_params.get(name, _undefined)
            if val is _undefined:
                val = await tc._task.parameters.get(name, _undefined)
                if val is _undefined:
                    raise ValueError(f'{name} not found in task parameters or path parameters')
            return converter(val, _request_context=tc)

        return getter

    @classmethod
    def _parse_handler_kwargs(cls, handler: FunctionT) -> FunctionKwargsT:
        """
        Rationale
        ---------
        - 此处假设处理器的签名是静态的，所以可以在路由记录实例化时解析参数备用，无需每次调用处理器之前重新解析
        - ``__call__`` 等调用处理器时将会使用解析的结果来自动注入参数

        Behaviour
        ----------
        参数解析规则
        ^^^^^^^^^^^^^^^
        - 跳过这些名称的参数
            - `self`, `cls`
        - 基于类型解析系统信息
            - `Response`, `Request`
        - 基于名称解析请求体参数（只能有一个，名称为 `HANDLER_BODY_KW` ）
        - 基于名称和类型解析路径参数、查询参数
            - 路径参数优先于查询参数
            - 名称匹配但类型不匹配会导致 `ValueError` 异常

        Dependency
        -----------
        - :meth:`scheme.converter.get_converter_from_anno`
        - `utils.type.get_origin`

        Returns
        -------
        返回一个字典，键为处理器的参数名称，值为该参数的获取器。

        参数获取器接收 :class:`blue_firmament.transport.context.RequestContext` 作为参数，从中解析出本参数需要的值。
        """
        handler_params_sig = inspect.signature(handler).parameters
        kwargs: TaskHandler.FunctionKwargsT = {}

        for name, param_sig in handler_params_sig.items():
            if name in ('self', 'cls'):
                continue

            anno = get_origin(param_sig.annotation)
            converter = get_converter_from_anno(param_sig.annotation)

            if safe_issubclass(anno, Task):
                kwargs[name] = lambda tc, _: tc._task
                continue
            elif safe_issubclass(anno, TaskResult):
                kwargs[name] = lambda tc, _: tc._task_result
                continue

            kwargs[name] = cls.get_param_getter(name, converter)

        return kwargs

    async def __call__(
        self, *,
        task_context: 'BaseTaskContext',
        path_params: PathParamsT,
    ) -> Body:
        """Run the inner handler.

        Behaviour
        ---------
        - 自动传递参数：基于实例化时解析的 `RequestHandlerKwargs`，从环境中解析出参数
        - 自动处理异步/同步函数：通过 `inspect.iscoroutinefunction` 判断函数是否为异步函数
        - 自动处理返回值：处理器的返回值会被解析到响应对象中
        """
        # get kwargs
        kwargs = {
            name: await getter(task_context, path_params)
            for name, getter in self.__handler_kwargs.items()
        }

        # get args
        args = []
        # [self] don't add other arg parser before this one
        if self.__method_manager_cls:
            manager = self.__method_manager_cls(task_context=task_context)
            args.append(manager)

        # call handler
        result = await call_as_async(self.__function, *args, **kwargs)

        # process result
        # TODO process result correctly
        if isinstance(result, Body):
            return result
        elif result is None:
            return EmptyBody()
        elif is_json_dumpable(result):
            return JsonBody(result)
        else:
            raise InternalError("handler returns invalid value")
