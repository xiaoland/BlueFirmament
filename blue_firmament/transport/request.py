from blue_firmament.session.common import CommonSession
from blue_firmament.transport.response import Response
from . import HeaderName, TransportOperationType
from .base import Connection, Cookie
from ..utils import dump_enum
from ..session import Session
import typing

if typing.TYPE_CHECKING:
    from ..routing import RouteKey


QueryParamsType = typing.NewType("QueryParamsType", typing.Dict[
    str, typing.Union[str, int, float, bool, list, None]
])
RequestBodyType = typing.Union[dict[str, typing.Any], str, bytes, None]

RequestSessionType = typing.TypeVar('RequestSessionType', bound=Session)
class Request(typing.Generic[RequestSessionType]):

    """碧霄请求类

    存储请求的相关信息；一个请求实例一定对应带来一个返回实例

    Data
    -----
    - conn: 连接实例
    - route_key: 路由键
    - session: 会话实例
    - query_params: 查询参数
    - headers: 请求头
    - cookies: Cookies(CookieJar)
    - body: 请求体

    Cookies
    ^^^^^^^^
    Cookie并不非得是HTTP中的Cookie，\n
    广义一点来说，是携带在请求中的、可以被客户端和服务端修改的简单数据，\n
    以用于在无状态协议中维持状态
    """

    def __init__(self,
        operation: TransportOperationType,
        path: str,
        conn: Connection,
        session_cls: typing.Type[RequestSessionType],
        query_params: QueryParamsType = QueryParamsType({}),
        headers: typing.Dict[str, str] = {},
        cookies: typing.Dict[str, Cookie] = {},
        body: RequestBodyType = None,
    ) -> None:

        from ..routing import RouteKey
        self.__route_key = RouteKey(operation, path)
        self.__conn = conn
        self.__session: typing.Optional[RequestSessionType] = None
        self.__session_cls: typing.Type[RequestSessionType] = session_cls
        self.__query_params: QueryParamsType = query_params
        self.__headers = headers
        self.__cookies = cookies
        self.__body = body

    @property
    def conn(self) -> Connection:
        return self.__conn

    @property
    def route_key(self) -> 'RouteKey':
        return self.__route_key

    @property
    def session(self) -> RequestSessionType:
        '''获取请求对应的会话实例'''

        if self.__session is None:
            self.__session = self.__session_cls.from_request(self)
        return self.__session

    def get_header(self, header_name: str | HeaderName) -> str | None:
        return self.__headers.get(dump_enum(header_name))

    def get_cookie(self, cookie_name: str) -> Cookie | None:
        return self.__cookies.get(cookie_name)

    @property
    def body(self) -> RequestBodyType: return self.__body

    @property
    def query_params(self) -> QueryParamsType:
        '''查询参数'''
        return self.__query_params


CommonSesstionRequest = typing.NewType("CommonSesstionRequest", Request[CommonSession])CommonSessionRequest = typing.NewType("CommonSessionRequest", Request[CommonSession])
CommonSessionRequest = typing.NewType("CommonSessionRequest", Request[CommonSession])
