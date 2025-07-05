import uvicorn
import enum
import typing
from typing import Optional as Opt
import json
import urllib.parse
from http.cookies import SimpleCookie
from ...task import Task, TaskID, TaskMetadata
from ...task.result import TaskResult, JsonBody, StreamingBody
from . import _types as http_types
from .base import MIMEType, HTTPHeader, TStatus2HCode
from ...utils import try_convert_str, dump_enum
from ..base import BaseTransporter
from ...task.main import Method, LazyParameter
from ...exceptions import BlueFirmamentException
from ..._types import _undefined

if typing.TYPE_CHECKING:
    from ...core.app import BlueFirmamentApp


TV = typing.TypeVar("TV")
class HTTPHeaders:
    """Parse ASGI headers to provide easy access to HTTP headers.

    :ivar __raw_headers: ASGI headers
    :ivar __parsed_headers:
    :ivar __headers: for create a response headers
    """

    def __init__(self,
        raw_headers: Opt[typing.Iterable[tuple[bytes, bytes]]] = None
    ):
        self.__raw_headers = raw_headers or ()
        self.__parsed_headers: dict[str, list[str] | str] = {}
        self.__headers: dict[str, str] = {}

    def _lookup_in_raw_headers(self, key: str) -> Opt[str | list[str]]:
        res: list[str] = []
        for header in self.__raw_headers:
            if key == header[0].decode('latin-1'):
                res.append(header[1].decode('latin-1'))

        if len(res) == 0:
            return None
        if len(res) == 1:
            return res[0]
        return res
    
    def get(self, key: str | enum.Enum, default: TV = None) -> list[str] | str | TV:
        res = self.__parsed_headers.get(dump_enum(key), None)
        if res is None:
            res = self._lookup_in_raw_headers(key)
            if res is None:
                return default
        return res

    def get_as_str(self, key: str | enum.Enum, default: TV = None) -> str | TV:
        res = self.get(key, default)
        if isinstance(res, str):
            return res
        else:
            raise TypeError("Header exist but value is not a string")
        
    def get_as_list(self, key: str | enum.Enum, default: TV = None) -> list[str] | TV:
        res = self.get(key, None)
        if isinstance(res, list):
            return res
        if res is None:
            return default
        else:
            return [res]
        
    def get_content_type(self) -> Opt[tuple[MIMEType, str]]:
        """Get 'Content-Type' in header

        :returns: a tuple, 0 for MIME type, 1 for charset

            If charset not set, defaults to `utf-8`
        """
        content_type_str = self.get_as_str(HTTPHeader.CONTENT_TYPE, None)
        if content_type_str is None:
            return None
        split = content_type_str.split(';')
        return MIMEType(split[0]), split[1].split('=')[1]

    def get_accept(self) -> tuple[MIMEType, ...]:
        """Get 'Accept' in header

        :returns: a list of MIME types that client accepts
        """
        accept_str = self.get_as_str(HTTPHeader.ACCEPT, None)
        if accept_str is None:
            return (MIMEType.JSON,)
        return tuple(
            MIMEType(i.strip().split(';')[0])
            for i in accept_str.split(',')
        )

    def get_accept_charset(self) -> tuple[str, ...]:
        """Get 'Accept-Charset' in header

        :returns: a string of charset that client accepts
        """
        accept_charset_str = self.get_as_str(HTTPHeader.ACCEPT_CHARSET, None)
        if accept_charset_str is None:
            return ('utf-8',)
        return tuple(
            i.strip().split(';')[0]
            for i in accept_charset_str.split(',')
        )

    @property
    def dict(self) -> dict[str, str]:
        return self.__headers

    def __setitem__(self, key: str | enum.Enum, value: str):
        self.__headers[dump_enum(key)] = value

    def set_content_type(self, mime_type: MIMEType, charset: str = "utf-8"):
        self[HTTPHeader.CONTENT_TYPE] = f"{dump_enum(mime_type)}; charset={charset}"


class HTTPBody(LazyParameter):
    """HTTP body as Task Parameter.

    Receive body bytes and parse it by MIMEType, encoding
    set in the header when needed. (lazy)
    """

    def __init__(
        self,
        receive: http_types.ASGIReceiveCallable,
        mime_type: MIMEType,
        content_encoding: str = 'utf-8',
    ):
        self.__receive = receive
        self.__mime_type = mime_type
        self.__encoding = content_encoding
        self.__parsed_body = _undefined

    async def get(self) -> typing.Any:
        if self.__parsed_body is _undefined:
            body_raw = b''
            while True:
                receive_chunk = await self.__receive()
                body_raw += receive_chunk.get('body', b'')
                if not receive_chunk.get('more_body', False):
                    break
            self.__parsed_body = self._parse_body(body_raw=body_raw)

        return self.__parsed_body

    def _parse_body(
        self, body_raw: bytes,
    ) -> typing.Union[dict[str, typing.Any], str, bytes, None]:
        """解析请求体

        将字节流根据内容类型解析为字典、字符串或字节流

        :param body_raw: 原始请求体
        :param mime_type: 内容类型
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

        """
        if not body_raw:
            return None

        mime_type = dump_enum(self.__mime_type)
        if mime_type == MIMEType.JSON.value:
            return json.loads(body_raw.decode(self.__encoding))
        elif mime_type == MIMEType.FORM.value:
            parsed_dict = {}
            pairs = urllib.parse.parse_qsl(body_raw.decode(self.__encoding))
            for key, value in pairs:
                if key in parsed_dict:
                    if isinstance(parsed_dict[key], list):
                        parsed_dict[key].append(try_convert_str(value))
                    else:
                        parsed_dict[key] = [parsed_dict[key], try_convert_str(value)]
                else:
                    parsed_dict[key] = try_convert_str(value)
            return parsed_dict
        elif mime_type == MIMEType.TEXT.value:
            return body_raw.decode(self.__encoding)
        elif mime_type == MIMEType.BINARY.value:
            return body_raw
        else:
            raise ValueError(f'Unsupported content type: {mime_type}')


class HTTPTransporter(BaseTransporter):
    """Transporter serves HTTP/S protocol.
    """

    def __init__(
        self,
        app: "BlueFirmamentApp",
        host: str,
        port: int,
        uds: Opt[str] = None,
        name: str = "default"
    ):
        """
        :param uds: Unix domain socket. E.g /tmp/blue_firmament.sock
        """
        super().__init__(app=app, name=name)
        self.__asgi_server = uvicorn.Server(uvicorn.Config(
            app=self, host=host, port=port, uds=uds
        ))

    def start(self):
        return self.__asgi_server.serve()

    async def __call__(self, 
        scope: http_types.Scope, 
        receive: http_types.ASGIReceiveCallable, 
        send: http_types.ASGISendCallable
    ):
        """
        `ASGI spec of applications <https://asgi.readthedocs.io/en/latest/specs/main.html#applications>`_
        """
        if scope['type'] == 'http':
            # parse headers
            headers = HTTPHeaders(scope['headers'])

            # parse cookies
            # TODO what to do with cookies?
            cookies = {}
            for cookie_str in headers.get_as_list('cookie', []):
                cookie = SimpleCookie()
                cookie.load(cookie_str)
                for name, morsel in cookie.items():
                    cookies[name] = morsel.value

            # compose task and task_result
            h_content_type = headers.get_content_type()
            task = Task(
                task_id=TaskID(
                    method=Method(scope['method']),
                    path=scope['path'],
                    separator='/'
                ),
                parameters={
                    "body": HTTPBody(
                        receive=receive,
                        mime_type=h_content_type[0],
                        content_encoding=h_content_type[1]
                    ),
                    **self.parse_query_params(scope['query_string'])
                },
                metadata=self.parse_metadata(headers)
            )
            task_result = TaskResult()

            try:
                await self._app.handle_task(
                    task=task, task_result=task_result, transporter=self
                )
            except BlueFirmamentException as e:
                task_result.status = e.task_status
                task_result.body = JsonBody(e.dump_details_to_dict())

            # send response
            try:
                res_headers = HTTPHeaders()
                if isinstance(task_result.body, JsonBody):
                    res_headers.set_content_type(MIMEType.JSON)
                elif isinstance(task_result.body, StreamingBody):
                    res_headers.set_content_type(MIMEType.EVENT_STREAM)
                    res_headers[HTTPHeader.CONNECTION] = "keep-alive"
                    res_headers[HTTPHeader.CACHE_CONTROL] = "no-cache"

                await send(http_types.HTTPResponseStartEvent(
                    type="http.response.start",
                    status=TStatus2HCode[task_result.status],
                    headers=task_result.metadata.dump_to_bytes(
                        encoding="latin-1",
                        extra=res_headers.dict
                    )
                ))

                async for chunk in task_result.body:
                    await send(http_types.HTTPResponseBodyEvent(
                        type="http.response.body",
                        body=chunk.dump_to_bytes(encoding="utf-8"),
                        more_body=True
                    ))

                await send(http_types.HTTPResponseBodyEvent(
                    type="http.response.body",
                    body=b'',
                    more_body=False
                ))
            except OSError:   # Disconnected unexpectedly
                self._logger.warning('Connection closed before all body were sent')
                task_result.body.cleanup()
        else:
            self._logger.warning(f"Request omitted due to unsupported protocol {scope['type']}")

    @staticmethod
    def parse_metadata(headers: HTTPHeaders) -> TaskMetadata:
        authorization=headers.get_as_str('authorization').split(" ")
        return TaskMetadata(
            authorization=(authorization[0], authorization[1]),
            trace_id=headers.get_as_str('x-trace-id'),
            client_id=headers.get_as_str('x-client-id'),
        )

    @staticmethod
    def parse_query_params(
        query_bytes: bytes,
        encoding: str = 'latin-1',
    ) -> dict[str, str | int | float | bool | None]:
        """解析查询参数

        将查询字符串解析为字典

        :param query_bytes: 查询字符串

        :raises ValueError: unsupported value type
        
        解析
        ^^^^^^
        - 尝试将值转换为布尔、整数或浮点数，如果失败则为字符串
        - 空字符串被转换为None
        
        """
        query_string = query_bytes.decode(encoding)
        parsed_dict = {}
        pairs: list[tuple[str, str]] = urllib.parse.parse_qsl(query_string)
        for key, value in pairs:
            parsed_dict[key] = try_convert_str(value)
        return parsed_dict
