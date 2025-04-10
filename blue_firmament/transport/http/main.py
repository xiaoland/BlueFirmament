import uvicorn
import typing
import json
import urllib.parse
import structlog

from ..request import Request
from ..response import Response
from . import _types as http_types
from ...utils import try_convert_str, call_function_as_async, dump_enum, get_when_truly

from ..base import (
    BlueFirmamentTransport, Connection, RequestHandlerType, ConnectionType,
    PeerInfo, Cookie
)
from ..request import RequestBodyType
from .. import TransportOperationType, ContentType, HeaderName

if typing.TYPE_CHECKING:
    from ...session import Session
    from ..request import QueryParamsType


logger = structlog.get_logger(__name__)


class HTTPTransport(BlueFirmamentTransport):

    """碧霄HTTP传输类

    是一个ASGI应用，实例化之后被ASGI服务器调用以处理请求
    """

    def __init__(self,
        req_handler: RequestHandlerType,
        session_cls: typing.Type['Session'],
        host: str,
        port: int             
    ):
        
        super().__init__(req_handler, session_cls)

        self.__server = uvicorn.Server(uvicorn.Config(self, host=host, port=port))

    async def __call__(self, 
        scope: http_types.Scope, 
        receive: http_types.ASGIReceiveCallable, 
        send: http_types.ASGISendCallable
    ):

        """ASGI应用启动接口
        
        每一个新连接将调用这个方法（不同类型的请求对新连接的定义不同）

        Documentation
        ^^^
        `ASGI spec of applications <https://asgi.readthedocs.io/en/latest/specs/main.html#applications>`_
        """
        if scope['type'] == 'http':

            # receive body
            body_raw: bytes = b''
            while True:
                receive_chunk = await receive()
                body_raw += receive_chunk.get('body', b'')
                if not receive_chunk.get('more_body', False):
                    break

            # parse headers
            headers = {}
            for header in scope['headers']:
                headers[header[0].decode('utf-8')] = header[1].decode('utf-8')
            content_type: str = headers.get(dump_enum(HeaderName.CONTENT_TYPE), ContentType.JSON) 
            content_encoding = headers.get(dump_enum(HeaderName.CONTENT_ENCODING), 'utf-8')

            # parse cookies
            cookies = {}
            cookies_string = headers.get(dump_enum(HeaderName.COOKIE))
            if cookies_string:
                cookies = dict(urllib.parse.parse_qsl(cookies_string, encoding=content_encoding))
                for key, value in cookies.items():
                    cookies[key] = Cookie(name=key, value=try_convert_str(value))

            # call request handler
            request = Request(
                operation=TransportOperationType(scope['method']),
                path=scope['path'],
                conn=Connection(
                    ConnectionType.from_asgi_scheme(scope['scheme']), 
                    self,
                    get_when_truly(scope['client'], PeerInfo.__call__), 
                    get_when_truly(scope['server'], PeerInfo.__call__), 
                ),
                session_cls=self._session_cls,
                body=self.parse_body(
                    body_raw=body_raw, 
                    content_type=content_type, 
                    content_encoding=content_encoding
                ),
                query_params=self.parse_query_params(scope['query_string']),
                headers=headers,
                cookies=cookies
            )
            response = Response()
            
            await call_function_as_async(self._request_handler, request, response)

            # send response
            try:
                await send({
                    "type": "http.response.start",
                    "status": response.http_status_code,
                })
                await send({
                    "type": "http.response.body",
                    "body": response.body.dump_to_bytes()
                })
            except OSError:
                # 连接关闭
                logger.warning('Connection closed before response sent')

    async def start(self):
        await self.__server.serve()

    @typing.overload
    @staticmethod
    def parse_body(
        body_raw: bytes,
        content_type: typing.Union[
            typing.Literal[ContentType.JSON],
            typing.Literal[ContentType.FORM],
        ],
        content_encoding: str = 'utf-8',
    ) -> dict | None:
        pass

    @typing.overload
    @staticmethod
    def parse_body(
        body_raw: bytes,
        content_type: typing.Literal[ContentType.TEXT],
        content_encoding: str = 'utf-8',
    ) -> str | None:
        pass

    @typing.overload
    @staticmethod
    def parse_body(
        body_raw: bytes,
        content_type: typing.Literal[ContentType.BINARY] | str,
        content_encoding: str = 'utf-8',
    ) -> bytes | None:
        pass

    @staticmethod
    def parse_body(
        body_raw: bytes,
        content_type: ContentType | str,
        content_encoding: str = 'utf-8',
    ) -> RequestBodyType:
        
        '''解析请求体

        将字节流根据内容类型解析为字典、字符串或字节流

        :param body_raw: 原始请求体
        :param content_type: 内容类型
        :param content_encoding: 内容编码；默认使用 `utf-8`

        Behaviour
        ---------
        - 如果不支持的内容类型，抛出 ``ValueError`` 异常
        
        解析
        ^^^^^^
        - ``application/json``: 解析为字典
        - ``application/x-www-form-urlencoded``: 解析为字典
            - 如果有重复的键，使用列表存储所有值
            - 尝试将值转换为布尔、整数或浮点数，如果失败则为字符串
            - 空字符串被转换为None
        - ``text/plain``: 解析为字符串
        - ``application/octet-stream``: 返回原始字节流

        '''
        if not body_raw:
            return None

        content_type = dump_enum(content_type)
        if content_type == ContentType.JSON.value:
            return json.loads(body_raw.decode(content_encoding))
        elif content_type == ContentType.FORM.value:
            parsed_dict = {}
            pairs = urllib.parse.parse_qsl(body_raw.decode(content_encoding))
            for key, value in pairs:
                if key in parsed_dict:
                    if isinstance(parsed_dict[key], list):
                        parsed_dict[key].append(try_convert_str(value))
                    else:
                        parsed_dict[key] = [parsed_dict[key], try_convert_str(value)]
                else:
                    parsed_dict[key] = try_convert_str(value)
            return parsed_dict
        elif content_type == ContentType.TEXT.value:
            return body_raw.decode(content_encoding)
        elif content_type == ContentType.BINARY.value:
            return body_raw
        else:
            raise ValueError(f'Unsupported content type: {content_type}')
        
    @staticmethod
    def parse_query_params(
        query_bytes: bytes,
        content_encoding: str = 'utf-8', 
    ) -> 'QueryParamsType':
        
        '''解析查询参数

        将查询字符串解析为字典

        :param query_string: 查询字符串

        Behaviour
        ---------
        - 如果不支持的内容类型，抛出 ``ValueError`` 异常
        
        解析
        ^^^^^^
        - 尝试将值转换为布尔、整数或浮点数，如果失败则为字符串
        - 空字符串被转换为None
        
        '''
        query_string = query_bytes.decode(content_encoding)
        parsed_dict = QueryParamsType({})
        pairs: list[tuple[str, str]] = urllib.parse.parse_qsl(query_string)
        for key, value in pairs:
            parsed_dict[key] = try_convert_str(value)
        return parsed_dict
