import asyncio
import typing

from .log import get_logger
from .transport import TransportOperationType
from .transport.response import Response
from .transport.request import CommonSesstionRequest, Request
from .transport import TransportOperationType
from .transport.base import (
    Connection, BlueFirmamentTransporter
)
from .transport.http import HTTPTransporter
from .session.common import CommonSession
from .scheme import BaseScheme, make_partial
from .utils import call_function_as_async
from .routing import Router
from .middleware import BaseMiddleware
from .dal.filters import *


logger = get_logger(__name__)

class BlueFirmamentApp:

    """碧霄应用

    实例化该类以创建一个碧霄应用，在（多个）指定的传输层上提供指定的服务
    """

    def __init__(self,
        name: str = 'BlueFirmamentApp',
        transports: typing.List[BlueFirmamentTransporter] | None = None,
        router: typing.Optional[Router] = None
    ):
        
        """
        :param router: （根）路由器实例，默认为None；如果为None，则会创建一个新的路由器实例
        """
        
        if typing.TYPE_CHECKING:
            self.__transports: typing.List[BlueFirmamentTransporter]
        
        self.__name__ = name
        self.__transports = transports or []
        
        if router is None:
            router = Router('root')
        self.__router = router

    def add_transporter(self, transporter: BlueFirmamentTransporter):

        """添加一个新的传输层

        :param transporter: 传输层实例
        """
        
        if not isinstance(transporter, BlueFirmamentTransporter):
            raise TypeError('transporter must be an instance of BlueFirmamentTransporter')
        
        self.__transports += (transporter,)

    def run(self):

        """启动应用

        Behaviour
        ^^^^^^^^^
        使用asyncio启动各个transport
        """
        event_loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(event_loop)
            
            tasks = [
                event_loop.create_task(transport.start()) 
                for transport in self.__transports
            ]

            event_loop.run_forever()
        except KeyboardInterrupt:
            logger.info('Stopping application...')
        finally:
            event_loop.stop()
            event_loop.close()

    async def handle_request(self, request: Request, response: Response):

        """处理新请求

        Impl
        -----
        1. 调用路由器路由该请求获得匹配的路由记录和路径参数
        2. 调用路由记录，路由记录会相应地调用处理函数
        3. 处理器返回结果后包装为返回对象

        返回包装
        ---------
        - 处理结果默认使用JSONResponse包装

        """
        route_record, path_params = self.__router.routing(request.route_key)

        # TODO build middlewares
        env = {
            'request': request, 
            'response': response, 
            'path_params': path_params or {}
        }
        middlewares: BaseMiddleware.MiddlewaresType = (
            route_record,
        )
        await call_function_as_async(
            middlewares[0], next = BaseMiddleware.get_next(middlewares, **env), **env
        )

    def handle_connection(self, conn: Connection):

        """
        处理新连接

        Implementation
        --------------
        创建新的状态实例并将其与连接绑定
        """
        # TODO
        pass

    def provide_crud_over_scheme(
        self, 
        name: str, 
        disabled_operations: typing.Iterable[TransportOperationType] = ()
    ):

        """为指定的数据模型提供CRUD服务

        用于装饰数据模型从而为该数据模型提供CRUD服务

        :param name: 业务模型名称

        Usage
        ^^^^^
        ```python
        @app.provide_crud_over_scheme('user')
        class UserScheme(BlueFirmamentScheme):
            _table_name = 'user'
            
            _id: int = Field(is_primary_key=True)
            name: str = 'default_name'
        ```

        路由注册结果
        ^^^^^^^^^^^^
        - `GET /<name>/<id>`：获取主键为`<id>`的数据模型数据
        - `POST /<name>`：创建一个新的数据模型
        - `PUT /<name>/<id>`：覆盖主键为`<id>`的数据模型（新数据模型在请求体中）
        - `PATCH /<name>/<id>`：更新主键为`<id>`的数据模型中的部分字段（请求体中说明）
        - `DELETE /<name>/<id>`：删除主键为`<id>`的数据模型
        """

        def wrapper(cls: typing.Type[BaseScheme]) -> typing.Type[BaseScheme]:
            
            # 注册路由
            if TransportOperationType.GET not in disabled_operations:
                self.__router.add_route_record(
                    TransportOperationType.GET, f'/{name}' + '/{id}', 
                    self.get_common_get_handler(cls)
                )
            if TransportOperationType.POST not in disabled_operations:
                self.__router.add_route_record(
                    TransportOperationType.POST, f'/{name}',
                    self.get_common_post_handler(cls)
                )
            if TransportOperationType.PUT not in disabled_operations:
                self.__router.add_route_record(
                    TransportOperationType.PUT, f'/{name}' + '/{id}', 
                    self.get_common_put_handler(cls)
                )
            if TransportOperationType.PATCH not in disabled_operations:
                self.__router.add_route_record(
                    TransportOperationType.PATCH, f'/{name}' + '/{id}',
                    self.get_common_patch_handler(cls)
                )
            if TransportOperationType.DELETE not in disabled_operations:
                self.__router.add_route_record(
                    TransportOperationType.DELETE, f'/{name}' + '/{id}', 
                    self.get_common_delete_handler(cls)
                )
            
            return cls
        
        return wrapper
    
    def get_common_get_handler(self, cls: typing.Type[BaseScheme]):

        '''获取基础的GET请求处理器

        Behaviour
        ----------
        - 使用数据模型主键从会话数据访问对象中获得数据模型实例
        - 主键值来源于路径参数 ``id``
        '''

        async def wrapper(
            request: CommonSesstionRequest,
            id
        ):
            return await request.session.dao.select_a_scheme_from_primary_key(
                cls, id
            )

        return wrapper
    
    def get_common_post_handler(self, cls: typing.Type[BaseScheme]):

        '''获取基础的POST请求处理器

        Behaviour
        ----------
        - 通过会话数据访问对象插入要创建的数据模型实例
        - 数据模型实例通过请求体（ ``body`` ）实例化
        - 请求体中不应该包含主键字段，如果有会被剔除
        '''
        async def wrapper(
            request: CommonSesstionRequest, 
            body: typing.Annotated[BaseScheme, cls]
        ):
            ins = cls(**body)
            return await request.session.dao.insert(ins)

        return wrapper
    
    def get_common_put_handler(self, cls: typing.Type[BaseScheme]):

        '''获取基础的PUT请求处理器

        Behaviour
        ----------
        - 通过会话数据访问对象覆盖要创建的数据模型实例
        - 数据模型实例通过请求体（ ``body`` ）实例化
        '''
        async def wrapper(
            request: CommonSesstionRequest, id, 
            body: typing.Annotated[BaseScheme, cls]
        ):
            ins = cls(**body)
            return await request.session.dao.update(
                ins, None, EqFilter(cls.get_primary_key(), id)
            )

        return wrapper
    
    def get_common_patch_handler(self, cls: typing.Type[BaseScheme]):

        '''获取基础的PATCH请求处理器

        Behaviour
        ----------
        - 通过会话数据访问对象更新要创建的数据模型实例
        - 数据模型实例使用部分化的数据模型类，数据为请求体（ ``body`` ）
        '''
        partial_cls = make_partial(cls)

        async def wrapper(
            request: CommonSesstionRequest, 
            id, body: typing.Annotated[BaseScheme, partial_cls]
        ):
            ins = partial_cls(**body)
            return await request.session.dao.update(
                ins, None, EqFilter(cls.get_primary_key(), id)
            )

        return wrapper
    
    def get_common_delete_handler(self, cls: typing.Type[BaseScheme]):

        '''获取基础的DELETE请求处理器

        Behaviour
        ----------
        - 通过会话数据访问对象删除要创建的数据模型实例
        - 数据模型实例通过路径参数 ``id`` 实例化
        '''
        async def wrapper(request: CommonSesstionRequest, id):
            return await request.session.dao.delete_a_scheme(
                cls, id
            )

        return wrapper
