import abc
import typing

from . import ResponseStatus
from .base import Cookie
from ..scheme import BaseScheme
from ..utils import singleton
from ..utils.type import JsonDumpable
from ..utils.json import dumps_to_json


ResponseBodyDataType = typing.TypeVar('ResponseBodyDataType')
class ResponseBody(abc.ABC, typing.Generic[ResponseBodyDataType]):

    """碧霄响应体类
    """

    def __init__(self, data: ResponseBodyDataType = None) -> None:
        self._data: ResponseBodyDataType = data

    @abc.abstractmethod
    def dump_to_dict(self) -> dict:
        pass

    @abc.abstractmethod
    def dump_to_bytes(self) -> bytes:
        '''将响应体序列化为字节流'''
        pass

    @abc.abstractmethod
    def dump_to_json(self) -> str:
        '''将响应体序列化为JSON字符串'''
        pass


@singleton
class EmptyResponseBody(ResponseBody):

    """空响应体
    """

    def dump_to_dict(self) -> dict:
        return {}

    def dump_to_bytes(self) -> bytes:
        return b''

    def dump_to_json(self) -> str:
        return ''


class JsonResponseBody(ResponseBody[JsonDumpable]):

    def __init__(self, data: JsonDumpable) -> None:
        super().__init__(data)

    def dump_to_dict(self) -> dict:
        if not isinstance(self._data, dict) and not isinstance(self._data, BaseScheme):
            raise TypeError('data is not dict or BaseScheme, cannot dump as dict, try dump_as_json() instread')
        if isinstance(self._data, BaseScheme):
            return self._data.dump_to_dict()
        return self._data

    def dump_to_bytes(self) -> bytes:
        return dumps_to_json(self.dump_to_dict()).encode('utf-8')

    def dump_to_json(self) -> str:
        return dumps_to_json(self.dump_to_dict())


class Response:

    """碧霄响应类

    存储请求的相关信息；一个请求实例一定对应带来一个返回实例
    """

    def __init__(self,
        response_status: ResponseStatus = ResponseStatus.OK,
        body: 'ResponseBody' = EmptyResponseBody(),
        headers: typing.Dict[str, str] = {},
        cookies: typing.Dict[str, Cookie] = {},
    ):
        self.__body: ResponseBody = body
        self.__response_status: ResponseStatus = response_status
        self.__headers: typing.Dict[str, str] = headers
        self.__cookies: typing.Dict[str, Cookie] = cookies

    @property
    def body(self) -> 'ResponseBody':
        '''响应体'''
        return self.__body

    @body.setter
    def body(self, value: 'ResponseBody') -> None:
        '''设置响应体'''
        self.__body = value

    @property
    def response_status(self) -> ResponseStatus:
        '''响应状态'''
        return self.__response_status

    @property
    def http_status_code(self) -> int:
        '''HTTP响应状态码'''
        return self.__response_status.value
