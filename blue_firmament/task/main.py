"""Task
"""

__all__ = [
    "TaskID",
    "TaskMetadata",
    "Task",
    "LazyParameter",
    "Method"
]

import abc
import dataclasses
import enum
import json
import types
import uuid
import typing
from typing import Optional as Opt

from ..utils import dump_enum, load_enum
from .._types import PathParamsT, Undefined, _undefined
from ..scheme.converter import AnyConverter, get_converter_from_anno

if typing.TYPE_CHECKING:
    from ..scheme.converter import BaseConverter


class Method(enum.Enum):
    GET = 'GET'
    POST = 'POST'
    PUT = 'PUT'
    PATCH = 'PATCH'
    DELETE = 'DELETE'
    OPTIONS = 'OPTIONS'


class TaskID:
    """Identifier of Task.

    Consist of a method and a path.
    Path is segmented by seperator, which optimizing
    performance, enhancing naming clarity.
    Path can have variable part, which is path parameter.
    Path parameter is named, match by position.
    Path parameter have type annotation, helps
    ensures parameters type safety.

    :ivar __param_converters: Map of parameter name to converter
        Contains all parameters' converters.
    """

    def __init__(
        self,
        method: Opt[Method | str],
        path: str,
        separator: str = '/',
        param_types: Opt[dict[str, typing.Type]] = None,
        param_converters: Opt[dict[str, "BaseConverter"]] = None
    ):
        """
        :param method:
            Action performed on the resource that path indicates.
            None is wildcard
        :param path: A URL-like path.
            Can include named positional parameters
            (e.g., '/users/{id}', 'users', 'users/').
        :param separator: Separator to split path into segments. Defaults to '/'.
        :param param_types: Path parameter's types.
            If not provided, all parameters will use AnyConverter.
            If conversion fails (value type safety failed), it's not considered a match.
        :param param_converters: Converter for path parameters.
            If not provided, inferred from param_types.
        """
        self.__method: Method = load_enum(Method, method)
        self.__path: str = path.replace(separator, '/').strip('/')
        """Normalized path"""

        self.__segments: typing.List[str] = path.strip(separator).split(separator)
        '''Path segmented by separator'''
        self.__dynamic_indices: typing.List[int] = []
        '''Dynamic segments(path parameters) indices'''
        for i, segment in enumerate(self.__segments):
            if segment.startswith('{') and segment.endswith('}'):
                # Dynamic segment, remove the brackets
                self.__segments[i] = segment[1:-1]
                self.__dynamic_indices.append(i)

        self.__param_converters: typing.Dict[str, BaseConverter]
        if param_types is None:
            param_types = {}
        if not param_converters:
            self.__param_converters = {}
            for dynamic_index in self.__dynamic_indices:
                param_name = self.__segments[dynamic_index]
                param_type = param_types.get(param_name, _undefined)
                if param_type is _undefined:
                    self.__param_converters[param_name] = AnyConverter()
                else:
                    self.__param_converters[param_name] = get_converter_from_anno(param_type)
        else:
            self.__param_converters = param_converters

    @staticmethod
    def resolve_dynamic_indices(raw_path: str) -> tuple[str, ...]:
        return tuple(
            i
            for i in raw_path.strip('/').split('/')
            if i.startswith('{') and i.endswith('}')
        )

    def __eq__(self, other):
        """Is two TaskID match.
        """
        if not isinstance(other, TaskID):
            return False
        return self.is_match(other) is not None

    def __hash__(self):
        return hash((self.method, *(i for i in self.segments)))

    def __str__(self):
        return f"{dump_enum(self.method) or ""}@{self.path}"

    def __len__(self) -> int:
        return len(self.segments)

    def __getitem__(self, key) -> 'TaskID':
        """使用slice获取子路由键
        """
        if isinstance(key, slice):
            return TaskID(self.__method, '/'.join(self.__segments[key]), param_converters=self.__param_converters)
        else:
            return TaskID(self.__method, self.__segments[key], param_converters=self.__param_converters)

    def dump_to_str(self) -> str:
        return self.__str__()

    @classmethod
    def load_from_str(cls, raw: str) -> typing.Self:
        method, path = raw.split("@", maxsplit=1)
        return cls(
            method=load_enum(Method, method or None),
            path=path,
        )

    def __is_segment_match(
        self,
        to_match_segment: str,
        my_segment_index: int
    ) -> types.NoneType | Undefined | typing.Any:
        """Whether a segment match another segment
        and resolve parameter if dynamic.

        :returns:
            If not match, return _undefined.
            If match and dynamic segment, return parameter value (converted).
            If match and static segment, return None.
        """
        if my_segment_index in self.__dynamic_indices:  # dynamic segment
            param_name = self.segments[my_segment_index]
            try:
                param_converter = self.__param_converters[param_name]
                return param_converter(to_match_segment)
            except KeyError:
                raise ValueError(f"No converter for parameter: {param_name}")
            except ValueError:
                return _undefined
        else:  # static segment
            return None if self.segments[my_segment_index] == to_match_segment else _undefined

    def fork(
        self,
        path_prefix: Opt[str] = None
    ) -> typing.Self:
        """

        :param path_prefix:
            Added to the front of the original path.
        :return: a new TaskID instance.
        """
        return TaskID(
            method=self.__method,
            path=f"{path_prefix}{self.__path}" if path_prefix else self.__path,
            param_converters=self.__param_converters,
        )

    @property
    def method(self) -> typing.Optional[Method]:
        return self.__method

    @property
    def path(self) -> str:
        """Normalized path.
        """
        return self.__path

    @property
    def segments(self) -> typing.List[str]:
        return self.__segments

    def is_dynamic(self) -> bool:
        """Is the TaskID dynamic.

        :return: If True, it's dynamic, otherwise static.
            Dynamic means it has path parameters or method is None (wildcard).
        """
        return len(self.__dynamic_indices) != 0 or self.__method is None

    def resolve_params(self, segments: list[str]) -> dict[str, typing.Any]:
        """Resolve path parameters from (static) segments.

        Returns
        ^^^
        - 字典键一定包含本路由键定义的所有参数
        - 如果参数校验不通过或不存在，则为 _undefined
        """
        result = {}

        for i in self.__dynamic_indices:
            param_name = self.__segments[i]
            try:
                param_converter = self.__param_converters[param_name]
                result[param_name] = param_converter(segments[i])
            except (IndexError, KeyError, ValueError):
                # IndexError: 我方不存在对应的分段
                # KeyError: 没有对应的参数校验器
                # ValueError: 校验不通过
                result[param_name] = _undefined

        return result

    def is_match(
        self,
        task_id: 'TaskID',
    ) -> Opt[PathParamsT]:
        """Whether another task_id match this task_id.

        :param task_id: TaskID to match.

        :returns: Path parameters when matched, otherwise None.

        Behaviours
        ^^^^^^^^^^
        - Is method match. If method is None(wildcard), skip.
        - Is path match.
            - If strict, length must match.
            - If path is static，比较我方路径分段（仅静态）是否为对方的子集（严格模式比较路径字符串）
            - 如果有路径参数，比较我方路径分段（包括静态与动态）是否为对方的子集（严格模式检验对方是否为我方子集）
                - 此处解析路径参数，如果未找到或校验不通过，则不记录
        """
        if not isinstance(task_id, TaskID):
            return None

        if self.method:
            if self.method != task_id.method:
                return None

        if len(self.segments) != len(task_id.segments):
            return None

        if not len(self.__dynamic_indices) == 0:
            # no dynamic segments, so we can compare segments directly
            return {} if self.segments == task_id.segments else None

        params = {}
        for i in range(len(task_id.segments)):
            seg_match = self.__is_segment_match(task_id.segments[i], i)
            if seg_match is _undefined:
                return None
            else:
                if seg_match is not None:
                    params[self.segments[i]] = seg_match

        return params


@dataclasses.dataclass
class TaskMetadata:
    """BlueFirmament Task Metadata
    """

    authorization: Opt[tuple[str, str]] = None
    """tuple(type, credentials)"""
    trace_id: Opt[str] = dataclasses.field(default_factory=lambda: str(uuid.uuid4()))
    client_id: Opt[str] = None

    def dump_to_bytes(
        self,
        encoding: str = 'latin-1',
        extra: Opt[dict] = None
    ) -> typing.Iterable[tuple[bytes, bytes]]:
        """Dump to iterable of (key, value) tuples, which key and value are bytes.

        :param extra: Extra data(in dict) to dump.
        """
        for field in dataclasses.fields(self):
            value = getattr(self, field.name)
            if value is not None:
                yield field.name.encode(encoding), str(value).encode(encoding)
        if extra:
            for key, value in extra.items():
                yield key.encode(encoding), str(value).encode(encoding)

    def dump_to_dict(self) -> dict[str, typing.Any]:
        return {
            field.name: getattr(self, field.name)
            for field in dataclasses.fields(self)
        }


class LazyParameter(abc.ABC):

    @abc.abstractmethod
    async def get(self) -> typing.Any:
        ...


TV = typing.TypeVar("TV")
class TaskParameters:

    def __init__(self, **parameters: typing.Any | LazyParameter):
        self.__parameters = parameters

    def __getitem__(self, item: str | enum.Enum):
        value = self.__parameters[dump_enum(item)]
        if isinstance(value, LazyParameter):
            raise TypeError("Use get() for LazyParameter")
        return value

    def items(self):
        return self.__parameters.items()

    async def get(self, item: str, default: TV = None) -> typing.Any | TV:
        value = self.__parameters.get(item, default)
        if isinstance(value, LazyParameter):
            return await value.get()
        return value

class Task:
    """Transport Task

    Task will be handled by handler and returns a result.

    Notes
    -----
    - Path parameters is not part of Task, cause task is created from transport layer,
    and path parameters are resolved by application layer. (This implies that task module
    is the glue layer between transport and application layers.)
    """

    def __init__(
        self,
        task_id: TaskID,
        metadata: Opt[TaskMetadata | dict] = None,
        parameters: Opt[dict[str, LazyParameter | typing.Any] | TaskParameters] = None,
    ) -> None:
        self.__task_id = task_id

        self.__parameters: TaskParameters
        if isinstance(parameters, dict):
            self.__parameters = TaskParameters(**parameters)
        elif isinstance(parameters, TaskParameters):
            self.__parameters = parameters
        else:
            self.__parameters = TaskParameters()

        if isinstance(metadata, dict):
            self.__metadata = TaskMetadata(**metadata)
        else:
            self.__metadata: TaskMetadata = metadata or TaskMetadata()

    @property
    def id(self) -> TaskID:
        return self.__task_id
    @property
    def trace_id(self) -> str:
        return self.__metadata.trace_id
    @property
    def metadata(self):
        return self.__metadata
    @property
    def parameters(self):
        return self.__parameters

    async def dump_to_bytes(self, encoding: str = "utf-8") -> bytes:
        return json.dumps({
            "task_id": self.__task_id.dump_to_str(),
            "metadata": self.__metadata.dump_to_dict(),
            "parameters": {
                key: value if not isinstance(value, LazyParameter) else await value.get()
                for key, value in self.__parameters.items()
            }
        }).encode(encoding)

    @classmethod
    def load_from_bytes(cls, raw: bytes, encoding: str = "utf-8") -> typing.Self:
        data = json.loads(raw.decode(encoding))
        task_id = TaskID.load_from_str(data["task_id"])
        metadata = TaskMetadata(**data["metadata"])
        parameters = TaskParameters(**data["parameters"])
        return cls(task_id, metadata, parameters)
