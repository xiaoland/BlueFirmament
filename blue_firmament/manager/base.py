import typing
import structlog
import typing_extensions
import types

from ..scheme.field import BlueFirmamentField
from ..transport import TransportOperationType
from ..session import Session
from ..scheme import BaseScheme

if typing.TYPE_CHECKING:
    from ..main import BlueFirmamentApp



SchemeType = typing.TypeVar('SchemeType', bound=BaseScheme)
'''管理器管理的数据模型类型'''
SessionType = typing_extensions.TypeVar('SessionType', bound=Session, default=Session)
'''管理器所属的会话类型

默认为 `session.common.CommonSession`
'''
T = typing.TypeVar('T')

class BaseManager(typing.Generic[SchemeType, SessionType]):

    '''管理器基类
    '''

    __scheme_cls__: typing.Type[SchemeType]
    '''管理器管理的数据模型类
    '''
    __path_prefix__: str
    '''管理器路径前缀

    - 蛇形小写
    - 建议与 所管理的数据模型的 DALPath[0] 对齐
    '''
    __manager_name__: str = ""
    '''管理器友好名称
    '''

    def __init__(self, 
        session: SessionType,
        logger: structlog.stdlib.BoundLogger
    ) -> None:

        self.__session: SessionType = session
        self.__logger: structlog.stdlib.BoundLogger = logger.bind(name=self.__manager_name__)
        self.__scheme: typing.Optional[SchemeType] = None

        # TODO also provide request and response

    @property
    def scheme_cls(self) -> typing.Type[SchemeType]:
        '''管理的数据模型类'''
        return self.__scheme_cls__

    @property
    def session(self) -> SessionType:
        '''当前会话'''
        return self.__session
    
    @property
    def logger(self) -> structlog.stdlib.BoundLogger:
        '''管理器级别日志记录器
        
        - 包含请求上下文信息
        - 添加 name 字段，为当前管理器的名称
        '''
        return self.__logger
    
    @property
    def dal_path(self):
        '''数据模型对应的 DALPath'''
        return self.scheme_cls.dal_path()

    @property
    def primary_key(self) -> BlueFirmamentField:
        '''数据模型主键字段'''
        return self.scheme_cls.get_primary_key()

    def get_primary_key_eqf(self, value: typing.Any):
        '''数据模型主键过滤器'''
        return self.scheme_cls.get_primary_key().equals(value)

    async def get_scheme(self, *args, **kwargs):

        '''获取管理的数据模型的实例

        数据模型实例为空时抛出 ``ValueError`` 异常
        '''

        if not self.__scheme:
            raise ValueError('scheme is None and no getter method provided')

        return self.__scheme
    
    def get_scheme_safe(self) -> SchemeType | None:

        """安全地获取数据模型实例

        有就是有，没有就是没有
        """
        return self.__scheme

    def set_scheme(self,
        scheme: SchemeType,
    ) -> None:

        '''设置本管理器实例当前管理的数据模型的实例

        :param scheme: 数据模型实例
        '''
        self.__scheme = scheme
    
    def derive_manager(self, manager_cls: typing.Type[T]) -> T:

        """派生管理器实例

        TODO 无需用户考虑 Session 是否匹配
        """
        if not issubclass(manager_cls, BaseManager):
            raise TypeError(f"manager_cls must be a subclass of {BaseManager.__name__}")
        
        return manager_cls(
            session=self.__session, logger=self.__logger
        )

    @classmethod
    def get_route_register(cls, app: "BlueFirmamentApp") -> "ManagerRouteRegister":
        """获取路由注册器

        :return: 路由注册器
        """
        return ManagerRouteRegister(
            app=app, 
            manager_cls=cls, 
            use_manager_prefix=True
        )


class ManagerRouteRegister:

    """管理器路由注册器

    用于将管理器中的处理器注册到 App 的根路由器中。
    """
    
    def __init__(self,
        app: "BlueFirmamentApp",
        manager_cls: typing.Type[BaseManager],
        use_manager_prefix: bool = True
    ) -> None:
        
        self._app = app
        self._manager_cls = manager_cls
        self._use_manager_prefix = use_manager_prefix
        self._register = self._app.router.get_manager_route_resigter(
            manager=self._manager_cls,
            use_manager_prefix=self._use_manager_prefix
        )

    def __enter__(self) -> typing.Self:
        return self

    def __exit__(self,
        exc_type: typing.Optional[typing.Type[BaseException]],
        exc_val: typing.Optional[BaseException],
        exc_tb: typing.Optional[types.TracebackType]
    ) -> None:
        # No specific cleanup needed for now
        pass

    def __call__(self,
        operation: TransportOperationType,
        path: str,
        handler: typing.Callable,
    ):
        
        """注册一个路由记录
        """
        return self._register(operation, path, handler)



