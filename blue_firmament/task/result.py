"""Task result module.
"""

__all__ = [
    "Body",
    "EmptyBody",
    "JsonBody",
    "StreamingBody",
    "TaskStatus",
    "TaskResult"
]

import abc
import json
import typing
from typing import Annotated as Anno, Optional as Opt, Literal as Lit
import enum

from . import TaskMetadata
from ..scheme import BaseScheme
from ..utils.main import singleton
from ..utils.typing_ import JsonDumpable


TV = typing.TypeVar('TV')
class Body(abc.ABC, typing.Generic[TV]):
    """Task Result Body
    """

    def __init__(self, data: TV = None) -> None:
        self._data: TV = data

    def dump_to_bytes(self, encoding: str = "utf-8") -> bytes:
        """Dump body to bytes.

        Extend supported value types by overriding this method,
        currently supported types are:
        - bytes
        - str (will be encoded to bytes using specified encoding)
        """
        if isinstance(self._data, bytes):
            return self._data
        if isinstance(self._data, str):
            return self._data.encode(encoding)
        raise NotImplementedError("This body is not supporting bytes serialization")

    def dump_to_dict(self) -> dict:
        if isinstance(self._data, dict):
            return self._data
        raise NotImplementedError("This body is not supporting dict serialization")

    def dump_to_json(self) -> str:
        try:
            return json.dumps(self._data, ensure_ascii=False)
        except TypeError:
            raise NotImplementedError('This body is not supporting JSON serialization')

    def dump_to_str(self) -> str:
        if isinstance(self._data, str):
            return self._data
        raise NotImplementedError("This body is not supporting str serialization")

    async def cleanup(self) -> None:
        pass


@singleton
class EmptyBody(Body):
    """Nothing here
    """

    def dump_to_dict(self) -> dict:
        return {}

    def dump_to_bytes(self, encoding: str = "utf-8") -> bytes:
        return b''

    def dump_to_json(self) -> str:
        return ''

class PlainTextBody(Body[str]):
    """Plain text body
    """

    def dump_to_str(self) -> str:
        return self._data

class JsonBody(Body[JsonDumpable]):

    def __init__(self, data: JsonDumpable) -> None:
        super().__init__(data)

    def dump_to_dict(self) -> dict:
        if not isinstance(self._data, (dict, BaseScheme)):
            raise TypeError(f'cannot dump {type(self._data)} to dict')
        if isinstance(self._data, BaseScheme):
            return self._data.dump_to_dict()
        return self._data

    def dump_to_bytes(self, encoding: str = "utf-8") -> bytes:
        return self.dump_to_json().encode(encoding)

    def dump_to_json(self) -> str:
        from ..utils.json_ import dumps_to_json
        return dumps_to_json(self._data)


class StreamingBody(Body):
    """An iterable body that yield events.

    :ivar __generator: 事件生成器
    :ivar __cleanup: 清理函数
    """

    type GeneratorType = typing.AsyncGenerator["Body", None]

    def __init__(
        self,
        generator: GeneratorType,
        cleanup: typing.Callable
    ) -> None:
        """
        :param generator:
            Event generator, yields Body other than StreamingBody.
        :param cleanup: Cleanup function to call when sending stopped unexpectedly.
        """
        super().__init__()
        self.__generator = generator
        self.__cleanup = cleanup

    def dump_to_bytes(self, encoding: str = "utf-8") -> bytes:
        raise NotImplementedError('This body is not supporting bytes serialization')

    def __aiter__(self) -> GeneratorType:
        return self.__generator
    
    async def cleanup(self) -> None:
        self.__cleanup()


class TaskStatus(enum.Enum):
    OK = 200
    CREATED = 201
    DELETED = 204
    BAD_REQUEST = 400
    UNPROCESSABLE_ENTITY = 422
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    UNAVAILABLE_FOR_LEGAL_REASONS = 451
    INTERNAL_SERVER_ERROR = 500
    NOT_IMPLEMENTED = 501
    SERVICE_UNAVAILABLE = 503


class TaskResult:

    def __init__(self,
        status: TaskStatus = TaskStatus.OK,
        body: Body = EmptyBody(),
        metadata: Opt[TaskMetadata] = None,
    ):
        self.__body: Body = body
        self.__status: TaskStatus = status
        self.__metadata: TaskMetadata = metadata or TaskMetadata()

    @property
    def metadata(self) -> TaskMetadata:
        return self.__metadata

    @property
    def body(self) -> Body:
        return self.__body

    @body.setter
    def body(self, value: Body) -> None:
        self.__body = value

    @property
    def status(self) -> TaskStatus:
        return self.__status
    
    @status.setter
    def status(self, value: TaskStatus) -> None:
        self.__status = value
