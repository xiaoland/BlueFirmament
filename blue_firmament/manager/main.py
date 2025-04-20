import typing
import typing_extensions

from blue_firmament.scheme.field import BlueFirmamentField
from ..dal.base import DataAccessObject
from ..session import Session
from ..session.common import CommonSession
from ..scheme import BaseScheme

if typing.TYPE_CHECKING:
    from ..main import BlueFirmamentApp



SchemeType = typing.TypeVar('SchemeType', bound=BaseScheme)
'''管理器管理的数据模型类型'''
SessionType = typing_extensions.TypeVar('SessionType', bound=Session, default=Session)
'''管理器所属的会话类型

默认为 `session.common.CommonSession`
'''

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

    def __init__(self, session: SessionType) -> None:

        self.__session: SessionType = session
        self.__scheme: typing.Optional[SchemeType] = None

    @property
    def scheme_cls(self) -> typing.Type[SchemeType]:
        '''本管理器管理的数据模型类'''
        return self.__scheme_cls__

    @property
    def session(self) -> SessionType:
        '''获取当前管理器的会话实例'''
        return self.__session
    
    @property
    def dal_path(self):
        return self.scheme_cls.dal_path()

    @property
    def primary_key(self) -> BlueFirmamentField:
        return self.scheme_cls.get_primary_key()

    def get_primary_key_eqf(self, value: typing.Any):
        return self.scheme_cls.get_primary_key().equals(value)

    async def get_scheme(self, *args, **kwargs):

        '''获取本管理器模型当前管理的的数据模型的实例

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

    @classmethod
    def get_route_record_register(cls,
        app: "BlueFirmamentApp"
    ):

        '''获取路由记录注册器

        这个注册器可以被用于注册本管理器中的处理器到该 app 的**根**路由器中
        '''

        return app.router.get_manager_handler_route_record_register(
            manager=cls, # type: ignore , this type error is brought by typevar default
            use_manager_prefix=True
        )