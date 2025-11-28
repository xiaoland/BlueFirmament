__all__ = [
    "BaseManager",
    # "BaseFieldManager"
]

import abc
import typing
from typing import Optional as Opt

from .._types import EventBusesT
from ..event.source.base import BaseEventSource
from ..event.registry import EventBus, EventEntry
from ..event.context import BaseEventContext
from ..exceptions import BFExceptionTV
from ..model.field import Field
from ..model import ModelTV
from ..log import log_manager_handler


class ManagerMetaclass(abc.ABCMeta):
    """Metaclass of Manager

    Terms
    -----
    Handlers are the methods excluding protected, private,
    classmethod, and staticmethod.

    Features
    --------
    Log enhancement
    ^^^^^^^^^^^^^^^
    Use :func:`blue_firmament.log.decorators.log_manager_handler` to decorate all handlers.
    A decorated handler will be skipped.

    Event bus
    ^^^^^^^^^
    Handlers decorated with :meth:`blue_firmament.event.listen_to` will be
    automatically added to manager event bus.

    """

    def __new__(
        cls,
        name: str,
        bases: tuple[type[typing.Any], ...],
        attrs: dict[str, typing.Any],
        path_prefix: str = "",
        **kwargs,
    ):
        # exclude BaseManager
        if name in ("BaseManager",):
            return super().__new__(cls, name, bases, attrs, **kwargs)

        attrs["__path_prefix__"] = path_prefix
        attrs["__event_registries__"]: dict[BaseEventSource | str, EventBus] = {}
        event_entries: list[tuple[tuple[BaseEventSource | str], EventEntry]] = []

        for attr_name, attr_value in attrs.items():
            # resolve event_entries
            if (
                isinstance(attr_value, tuple)
                and len(attr_value) == 2
                and isinstance(attr_value[0], tuple)
                and isinstance(attr_value[1], EventEntry)
            ):
                event_entry = attr_value[1]
                entry_handlers = event_entry.handlers
                # unwrap handler
                if len(entry_handlers) != 1:
                    raise ValueError("Must have exactly one handler")
                attrs[attr_name] = entry_handlers[0].function
                # add to entries
                event_entries.append(attr_value)
                # make later resolution works
                attr_value = attrs[attr_name]

            if attr_name.startswith("_"):
                continue

            # log enhancement
            if callable(attr_value):
                if not isinstance(attr_value, (classmethod, staticmethod)):
                    attrs[attr_name] = log_manager_handler(attr_value)

        new_cls = super().__new__(cls, name, bases, attrs, **kwargs)

        if not issubclass(new_cls, BaseManager):
            raise TypeError(f"{name} should not directly use the ManagerMetaclass")

        # set event handlers' manager class
        for i in event_entries:
            i[1].set_manager_cls(new_cls)
            for event_source in i[0]:
                attrs["__event_registries__"].setdefault(
                    event_source,
                    EventBus(name=str(event_source), path_prefix=path_prefix),
                ).add_entry(i[1])

        return new_cls


T = typing.TypeVar("T")


class BaseManager(
    typing.Generic[ModelTV],
    BaseEventContext,
    metaclass=ManagerMetaclass,
):
    """Base class of manager.

    Configuration
    -------------
    Config through bases parameters.
    """

    __scheme_cls__: type[ModelTV]
    """Scheme class this manager is managing
    """
    __event_registries__: EventBusesT
    """Event buses of this manager
    """
    __manager_name__: str
    """Friendly name of this manager.

    - no ``manager``
    - use ``_`` and lowercase
    """
    __path_prefix__: str

    class ManagingScheme:
        def __init__(self, scheme: Opt[ModelTV] = None):
            self.__scheme: Opt[ModelTV] = scheme

        def set(self, scheme: ModelTV):
            self.__scheme = scheme

        def get(self) -> ModelTV:
            return self.__scheme

        def __bool__(self):
            return self.__scheme is not None

    def __init_subclass__(
        cls,
        scheme_cls: Opt[type[ModelTV]] = None,
        manager_name: Opt[str] = None,
        **kwargs,
    ):
        if scheme_cls:
            cls.__scheme_cls__ = scheme_cls
        if manager_name:
            cls.__manager_name__ = manager_name

        super().__init_subclass__(**kwargs)

    def __init__(self, event_context: BaseEventContext) -> None:
        BaseEventContext.__init__(self, event_context)

        self.__scheme = self.ManagingScheme(None)
        self._logger = self._logger.bind(manager_name=self.__manager_name__)
        self.__post_init__()

    def __post_init__(self):
        """Override this method to customize init behaviour

        This method will be called once BaseManager finish its init.
        """
        ...

    @property
    def _scheme_cls(self) -> typing.Type[ModelTV]:
        """Managing scheme class"""
        return self.__scheme_cls__

    @property
    def _dal_path(self):
        """DALPath of managing scheme"""
        return self._scheme_cls.dal_path()

    @property
    def _scheme_key(self) -> Field:
        """Key field of managing scheme"""
        return self._scheme_cls._get_key_field()

    @property
    def _scheme(self) -> ModelTV:
        """Managing scheme

        :raise ValueError: scheme not set
        """
        if not self.__scheme:
            raise ValueError("scheme is not set")
        return self.__scheme.get()

    @_scheme.setter
    def _scheme(self, scheme: ModelTV):
        """Set managing scheme"""
        self.__scheme.set(scheme)

    def _try_get_scheme(self) -> Opt[ModelTV]:
        """Get scheme without exception"""
        try:
            return self._scheme
        except ValueError:
            self._logger.warning("Scheme not set")
            return None

    def _get_bfe(
        self, exception: typing.Type[BFExceptionTV], *args, **kwargs
    ) -> BFExceptionTV:
        """获取碧霄异常实例

        携带和日志器一致的上下文信息
        """

        return exception(*args, **kwargs, **self._logger._context)


# class ManagerRouteRegister:

#     """管理器路由注册器

#     用于将管理器中的处理器注册到 App 的根路由器中。
#     """

#     def __init__(self,
#         app: "BlueFirmamentApp",
#         manager_cls: typing.Type[BaseManager],
#         use_manager_prefix: bool = True
#     ) -> None:

#         self._app = app
#         self._manager_cls = manager_cls
#         self._use_manager_prefix = use_manager_prefix
#         self._register = self._app.router.get_manager_route_resigter(
#             manager=self._manager_cls,
#             use_manager_prefix=self._use_manager_prefix
#         )

#     def __enter__(self) -> typing.Self:
#         return self

#     def __exit__(self,
#         exc_type: typing.Optional[typing.Type[BaseException]],
#         exc_val: typing.Optional[BaseException],
#         exc_tb: typing.Optional[types.TracebackType]
#     ) -> None:
#         # No specific cleanup needed for now
#         pass

#     def __call__(self,
#         operation: Method,
#         path: str,
#         handler: typing.Callable,
#     ):

#         """注册一个路由记录
#         """
#         return self._register(operation, path, handler)


# BaseManagerTV = typing.TypeVar("BaseManagerTV", bound=BaseManager)
# class BaseFieldManager(
#     typing.Generic[
#         T,
#         BaseManagerTV,
#         SessionTV
#     ],
#     BaseEventContext[SessionTV],
#     metaclass=ManagerMetaclass,
# ):
#     """字段管理器基类

#     Example
#     -------
#     .. code-block:: python
#         from blue_firmament.scheme import BlueFirmamentField, BaseScheme, BaseManager
#         from blue_firmament.manager import BaseFieldManager

#         class MessageContent(BlueFirmamentField):
#             def __init__(self):
#                 super().__init__(default="Hello World")

#         class Message(BaseScheme):
#             content: MessageContent

#         class MessageManager(BaseManager[Message, CommonSession]):
#             __scheme_cls__ = Message

#         class MessageContentManager(BaseFieldManager[MessageContent, CommonSession]):
#             __field_cls__ = MessageContent
#             __scheme_manager_cls__ = MessageManager
#     """

#     __scheme_manager_cls__: typing.Type[BaseManagerTV]
#     """所管理字段所属数据模型的管理器类
#     """
#     __field__: Field[T]
#     """管理器管理的字段类
#     """
#     __path_prefix__: str
#     """管理器路径前缀
#     """
#     __manager_name__: str = "UnknownFieldManager"
#     """管理器友好名称
#     """

#     def __init__(self, request_context: BaseEventContext) -> None:

#         self.init_from_tc(request_context)

#         self._field_value: Opt[T] = None
#         """管理的字段值"""
#         self.__scheme_manager: BaseManagerTV = self.__scheme_manager_cls__(request_context)
#         self.__logger: LoggerT = self._logger.bind(
#             name=self.__manager_name__
#         )
#         """管理器级别日志记录器"""

#     @property
#     def _logger(self) -> LoggerT:

#         """管理器级别日志记录器
#         """
#         return self.__logger

#     @property
#     def field(self) -> Field[T]:
#         """管理的字段实例"""
#         return self.__field__

#     @property
#     def scheme_manager(self) -> BaseManagerTV:
#         """管理的字段所属数据模型的管理器实例"""
#         return self.__scheme_manager

#     @property
#     def value(self) -> T:
#         """当前管理的字段值"""
#         if not self._field_value:
#             raise ValueError('field value is None')
#         return self._field_value

#     @classmethod
#     def get_route_register(cls, app: "BlueFirmamentApp") -> "ManagerRouteRegister":
#         """获取路由注册器
#         """
#         return ManagerRouteRegister(
#             app=app,
#             manager_cls=cls,  # TODO type safe
#             use_manager_prefix=True
#         )
