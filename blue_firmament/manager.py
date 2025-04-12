'''Manager of BlueFirmament'''

import typing

from .session import Session
from .scheme import BaseScheme

if typing.TYPE_CHECKING:
    from .dal import DataAccessObject
    from .main import BlueFirmamentApp


SchemeType = typing.TypeVar('SchemeType', bound=BaseScheme)
SessionType = typing.TypeVar('SessionType', bound=Session)
class BaseManager(typing.Generic[SchemeType, SessionType]):

    '''管理器基类
    '''

    __SCHEME_CLS__: typing.Type[SchemeType]
    __name__: str
    '''管理器名称；用作路由路径前缀'''

    def __init__(self, session: SessionType) -> None:
        
        self.__session: SessionType = session
        self.__scheme: typing.Optional[SchemeType] = None

    @property
    def session(self) -> SessionType:
        '''获取当前管理器的会话实例'''
        return self.__session

    async def get_scheme(self,
        from_primary_key: typing.Any = None,
    ) -> SchemeType:
        
        '''获取本管理器管理的数据模型的实例

        :param from_primary_key: 主键值，不为None则在无实例时从主键获取

        行为
        ----------
        - 如果没有数据模型实例，则尝试下列方法：
            - 通过当前会话的 DAO 以及主键值获取数据模型实例
        - 上述方法都不通过，则抛出 ``ValueError`` 异常

        外部依赖
        ------------
        - 使用 from_primary_key 时管理器所属会话必须有DAO字段
        '''
        
        if not self.__scheme:
            if from_primary_key:
                self.__scheme = await typing.cast(
                    DataAccessObject,
                    self.session.dao
                ).select_a_scheme_from_primary_key(
                    self.__SCHEME_CLS__, from_primary_key
                )
            else:
                raise ValueError('scheme is None and no getter method provided')

        return self.__scheme
    
    def set_scheme(self,
        scheme: SchemeType,
    ) -> None:
        
        '''设置本管理器管理的数据模型的实例

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
            manager=cls, use_manager_name_as_prefix=True
        )
