"""数据模型转换器

数据模型转换器尽可能地保证数据的类型安全、值安全，
常用于数据模型字段中
"""

import abc
import datetime
import typing
import enum
import types
from typing import Optional as Opt

from .._types import NamedTupleTV, Undefined
from .._types import _undefined
from ..utils.typing_ import JsonDumpable, get_origin, is_json_dumpable, is_namedtuple, safe_issubclass
from ..utils.main import singleton

if typing.TYPE_CHECKING:
    from . import BaseScheme


T = typing.TypeVar('T')
SchemeTV = typing.TypeVar('SchemeTV', bound='BaseScheme')
EnumMemberTV = typing.TypeVar('EnumMemberTV', bound=enum.Enum)
ConverterResultTV = typing.TypeVar('ConverterResultTV')
ConverterModeT = typing.Literal['base'] | typing.Literal['strict']
class ConverterProtocol(typing.Protocol):

    def __call__(self, value: typing.Any) -> typing.Any:
        """转换值
        """
        ...


class BaseConverter(typing.Generic[ConverterResultTV], abc.ABC):
    
    """碧霄转换器基类

    Features
    --------
    将任意输入转换为指定的类型，并保证其值合法

    模式
    ^^^^^^
    - 基本模式 `base`：即便类型不匹配，仍然尝试转换为目标类型，成功则视为通过并返回转换值
    - 严格模式 `strict`：类型不匹配则直接抛出异常
    - 子校验器不在初始化器中接受该参数，可以在调用或者直接修改mode属性来设置

    序列化
    ^^^^^^^^
    即逆转换
    
    Examples
    --------
    >>> sc = StrConverter(min_len=3, max_len=5)
    >>> sc('abc')
    'abc'
    >>> sc('ab')
    ValueError: Value 'ab' is less than minimum length 3

    """

    def __init__(self, mode: ConverterModeT = 'base') -> None:
        self.mode = mode

    @property
    def is_base(self): return self.mode == 'base'
    @property
    def is_strict(self): return self.mode == 'strict'

    @property
    @abc.abstractmethod
    def type(self) -> typing.Type[ConverterResultTV]:
        """转换结果类型注释"""
        ...
    
    @abc.abstractmethod
    def __call__(self, value, **kwargs) -> ConverterResultTV:
        """转换值
        """
        raise NotImplementedError('`__call__` method must be implemented in subclass')
    
    def dump(self, value: ConverterResultTV) -> typing.Any:

        """序列化值
        """
        return value
    
    def dump_to_str(self, value: ConverterResultTV) -> str:
        """Dump value to string
        """
        return str(value)
    
    def dump_to_jsonable(self, value: ConverterResultTV) -> JsonDumpable:

        """Dump value to jsonable value
        """
        if is_json_dumpable(value):
            return value
        else:
            raise TypeError("cannot dump type %s" % type(value))
    

def get_converter_from_anno(
    tp: typing.Type
) -> BaseConverter:
    
    """根据类型注释获取转换器

    Behaviour
    ---------
    - 找不到合适的校验器则返回通用校验器 :class:`AnyConverter`
    - 支持枚举、数据模型
    - 支持 NewType, UnionType, Annotated, Optional
    - Support NamedTuple

    Example
    -------
    >>> get_converter_from_anno(typing.Annotated[str, StrConverter(min_len=3)])
    StrConverter(min_len=3)
    >>> get_converter_from_anno(typing.Union[str, int])
    UnionConverter[str, int]
    >>> get_converter_from_anno(typing.Union[str, None])
    OptionalConveter[str]
    >>> get_converter_from_anno(typing.Optional[str])
    OptionalConveter[str]
    """
    from .main import BaseScheme

    ortp = get_origin(tp)
    if safe_issubclass(ortp, BaseScheme):
        return SchemeConverter(ortp)
    if safe_issubclass(ortp, enum.Enum):
        return EnumConverter(ortp)

    if ortp is int:
        return IntConverter()
    if ortp is float:
        return FloatConverter()
    if ortp is str:
        return StrConverter()
    if ortp is None:
        return NoneConverter()
    if ortp is datetime.datetime:
        return DatetimeConverter()
    if ortp is set:
        return SetConverter(
            element_type=typing.get_args(tp)[0]
        )
    if ortp is dict:
        return DictConverter(
            value_type=typing.get_args(tp)[0]
        )
    if is_namedtuple(ortp):
        return NamedTupleConveter(
            namedtuple_type=tp
        )
    if ortp is tuple:
        return TupleConverter(
            tuple_type=tp
        )

    # parse union type and optional type
    if typing.get_origin(tp) is typing.Union:
        args = typing.get_args(tp)
        # if one is None, it's optional
        if len(args) == 2 and (
            args[1] is types.NoneType or args[0] is types.NoneType
        ):
            return OptionalConveter(args[1] if args[1] is not types.NoneType else args[0])

        return UnionConverter(*args)
    
    return AnyConverter()



@singleton
class AnyConverter(BaseConverter[typing.Any]):
    
    """
    通用转换器

    不做任何转换，只是返回原值
    """
    
    def __call__(self, value: typing.Any, **kwargs) -> typing.Any: 
        return value
    
    @property
    def type(self): return typing.Type[typing.Any]


class SchemeConverter(BaseConverter[SchemeTV], typing.Generic[SchemeTV]):

    """数据模型转换器
    """

    def __init__(self, 
        scheme_cls: typing.Type[SchemeTV],
        mode: ConverterModeT = 'base'
    ) -> None:
        
        super().__init__(mode)
        self.scheme_cls = scheme_cls

    def __call__(self, value: dict | SchemeTV, **kwargs) -> SchemeTV:

        """
        :param value: 序列化值
        :param kwargs: 额外参数

            - _request_context: 请求上下文
        """
        if isinstance(value, dict):
            return self.scheme_cls(**value, **kwargs)
        else:
            for k, v in kwargs:
                value[k] = v
            return value

    @property
    def type(self): return self.scheme_cls

    def dump_to_jsonable(self, value): 
        return value.dump_to_dict(jsonable=True)


class EnumConverter(BaseConverter[EnumMemberTV], typing.Generic[EnumMemberTV]):

    """枚举转换器
    """

    def __init__(self, 
        enum_cls: typing.Type[EnumMemberTV],
        mode: ConverterModeT = 'base'
    ) -> None:
        
        super().__init__(mode)
        self.enum_cls = enum_cls

    def __call__(self, value, **kwargs) -> EnumMemberTV:
        return self.enum_cls(value)
    
    @property
    def type(self): return self.enum_cls

    def dump_to_jsonable(self, value): return value.value
    def dump_to_str(self, value): return value.value

class EnumValueConverter(BaseConverter):

    def __call__(self, value, **kwargs) -> typing.Any:
        if not isinstance(value, enum.Enum):
            raise ValueError("not enum member")
        return value.value
    
    @property
    def type(self): return typing.Type[typing.Any]


# TODO union typevar
class UnionConverter(BaseConverter):

    """联合类型转换器

    只要一组转换器中有一个转换成功就有效（子转换器为严格模式）
    """

    def __init__(self, 
        *types_: typing.Type,
        mode: ConverterModeT = 'base'
    ) -> None:
        super().__init__(mode)

        self.sub_conveters = []
        for type_ in types_:
            converter = get_converter_from_anno(type_)
            converter.mode = 'strict'
            self.sub_conveters.append(converter)

    def __call__(self, value: typing.Any, **kwargs) -> typing.Any:

        for converter in self.sub_conveters:  # 将频次较高的放在前面，效率就更高
            try:
                return converter(value)
            except ValueError:
                continue

    @property
    def type(self): 
        return typing.Type[
            typing.Union[*tuple(validator.type for validator in self.sub_conveters)]
        ]

class OptionalConveter(BaseConverter[typing.Optional[ConverterResultTV]]):

    def __init__(self, 
        tp: Undefined | typing.Type[ConverterResultTV] = _undefined,
        tp_converter: Opt[BaseConverter[ConverterResultTV]] = None,
        mode: ConverterModeT = 'base'
    ):
        super().__init__(mode)

        if not tp_converter:
            if tp is _undefined:
                raise ValueError('`tp` or `tp_converter` must be provided')
            self.sub_converter = get_converter_from_anno(tp)

    def __call__(self, value, **kwargs) -> ConverterResultTV | types.NoneType:
        
        try:
            NoneConverter()(value)
        except ValueError:
            return self.sub_converter(value)
        
    @property
    def type(self): return typing.Type[typing.Optional[self.sub_converter.type]]

class IntConverter(BaseConverter[int]):
    
    """整型转换器

    Features
    --------
    可以校验：
    - 大小
    - 奇偶性
    """

    def __init__(self, 
        ge: Opt[int] = None, le: Opt[int] = None,
        mode: ConverterModeT = 'base'
    ):
        
        super().__init__(mode)

        self.ge = ge
        self.le = le

    def __call__(self, value: typing.Any, **kwargs) -> int:
        
        res = int(value)
        if self.ge is not None and res <= self.ge:
            raise ValueError(f'Value {res} is less than minimum {self.ge}')
        if self.le is not None and res >= self.le:
            raise ValueError(f'Value {res} is greater than maximum {self.le}')
        return res
    
    @property
    def type(self): return int


class FloatConverter(BaseConverter[float]):
    """
    Features
    --------
    - number range
    """

    def __init__(self, 
        gt: Opt[float] = None, ge: Opt[float] = None, 
        lt: Opt[float] = None, le: Opt[float] = None,
        mode: ConverterModeT = 'base'
    ):  
        """
        If gt provided, don't provide ge, which is same for lt.
        Since ge prior to gt.
        """

        super().__init__(mode)

        self.gt = gt
        self.lt = lt
        self.ge = ge
        self.le = le

    def __call__(self, value: typing.Any, **kwargs) -> float:
        
        if not isinstance(value, float):
            if self.is_base:
                value = float(value)
            else:
                raise ValueError(f'Value {value} is not float')
        
        if self.ge is not None and value <= self.ge:
            raise ValueError(f'Value {value} is less than minimum {self.ge}')
        if self.le is not None and value >= self.le:
            raise ValueError(f'Value {value} is greater than maximum {self.le}')
        if self.gt is not None and value < self.gt:
            raise ValueError(f'Value {value} is less(or equal) than minimum {self.gt}')
        if self.lt is not None and value > self.lt:
            raise ValueError(f'Value {value} is greater(or equal) than maximum {self.lt}')
        return value
    
    @property
    def type(self): return float
    

class StrConverter(BaseConverter[str]):

    """字符串转换器
    """

    def __init__(self, 
        min: Opt[int] = None, max: Opt[int] = None,
        allow_empty: bool = False,
        half_as_unit: bool = False,
        mode: ConverterModeT = 'base'
    ):
        
        """
        :param min: 最小长度
        :param max: 最大长度
        :param allow_empty: 允许空字符串
        :param half_as_unit: 半宽字符作为长度基本单位
            
            - True: 1:1
            - False: 1:2
        """

        super().__init__(mode)

        self.min_len = min
        self.max_len = max
        self.allow_empty = allow_empty
        self.half_as_unit = half_as_unit

    def get_length(self, value: str) -> int:
        """获取字符串长度
        """
        if self.half_as_unit:
            return len(value)
        else:
            return sum(2 if ord(i) > 255 else 1 for i in value) # TESTME 

    def __call__(self, value, **kwargs) -> str:
        
        res = ''
        if self.is_base:
            res = str(value)
        if self.is_strict:
            if not isinstance(value, str):
                raise ValueError(f'Value {value} is not str')
            res = value

        length = self.get_length(res)
        if self.min_len is not None and length < self.min_len:
            if length == 0 and self.allow_empty:
                return res
            raise ValueError(f'Value {res} is less than minimum length {self.min_len}')
        if self.max_len is not None and length > self.max_len:
            raise ValueError(f'Value {res} is greater than maximum length {self.max_len}')
        
        return res
    
    @property
    def type(self): return str


@singleton
class NoneConverter(BaseConverter[None]):
    
    """None转换器

    有效值
    -----
    严格模式
    ^^^^^^^^^
    - None
    基本模式
    ^^^^^^^^^
    - 'null'
    - 'undefined'
    """

    def __call__(self, value: typing.Any, **kwargs) -> None:

        if value is not None:
            if self.is_base:
                # try from string
                if isinstance(value, str):
                    if value == 'null':
                        return None

            raise ValueError(f'Value {value} is not None')
        return None
    
    @property
    def type(self): return types.NoneType


TupleValueTV = typing.TypeVarTuple('TupleValueTV')
class TupleConverter(
    BaseConverter[tuple[typing.Unpack[TupleValueTV]]], 
    typing.Generic[typing.Unpack[TupleValueTV]]
):

    """元组转换器

    按照顺序校验每个元素的值，长度必须一致
    """

    def __init__(self, 
        tuple_type: typing.Type[tuple[typing.Unpack[TupleValueTV]]],
        mode: ConverterModeT = 'base'
    ):
        super().__init__(mode)
        
        self.sub_converters: typing.Tuple[BaseConverter, ...] = tuple(
            get_converter_from_anno(type_) 
            for type_ in typing.get_args(tuple_type)
        )

    def __call__(self, value, **kwargs) -> tuple[typing.Unpack[TupleValueTV]]:
        
        if not isinstance(value, tuple):
            if self.is_base:
                value = tuple(value)

        if len(value) != len(self.sub_converters):
            raise ValueError(f'Value {value} is not a tuple of length {len(self.sub_converters)}')
        
        return tuple(
            validator(value[i]) 
            for i, validator in enumerate(self.sub_converters)
        )
    
    @property
    def type(self): return typing.Tuple[*tuple(
        validator.type 
        for validator in self.sub_converters
    )]

    def dump_to_jsonable(self, value) -> tuple: 
        return tuple(
            self.sub_converters[i].dump_to_jsonable(value[i])
            for i in range(len(value))
        )
    

class NamedTupleConveter(BaseConverter[NamedTupleTV], typing.Generic[NamedTupleTV]):
    """带名元组转换器
    """

    def __init__(self, 
        namedtuple_type: typing.Type[NamedTupleTV],
        mode: ConverterModeT = 'base'
    ):
        super().__init__(mode)
        self.namedtuple_cls: typing.Type[NamedTupleTV] = namedtuple_type
        self.sub_validators = tuple(
            get_converter_from_anno(i)
            for i in self.namedtuple_cls.__annotations__.values()
        )
    
    def __call__(self, value, **kwargs) -> NamedTupleTV:

        if type(value) is self.namedtuple_cls:
            return value
        
        if not isinstance(value, tuple):
            value = TupleConverter(typing.Tuple[typing.Any, ...])(value)
        
        if len(value) != len(self.namedtuple_cls._fields):
            raise ValueError(f"Value {value} is not a namedtuple of length {len(self.namedtuple_cls._fields)}")
        
        # TODO support default value
        
        converted_values = tuple(
            self.sub_validators[i](value[i])
            for i in range(len(value))
        )
        return self.namedtuple_cls(*converted_values) # type: ignore
        # FIXME type issue
    
    @property
    def type(self): return self.namedtuple_cls


class SetConverter(BaseConverter[typing.Set[T]], typing.Generic[T]):
    """集合转换器
    
    Behaviour
    ---------
    校验内容
    ^^^^^^^^^
    - 是集合
    - 集合元素类型
    """

    def __init__(self, 
        element_type: typing.Type[T],
        mode: ConverterModeT = 'base'
    ):
        
        super().__init__(mode)
        self.sub_conveter: BaseConverter[T] = get_converter_from_anno(element_type)

    def __call__(self, value, **kwargs) -> set:
        
        # is a set
        if not isinstance(value, set):
            if self.is_base:
                value = set(value)
            
            raise ValueError(f"Value {value} is not set")
        
        # validate element type
        new_value: typing.Set[T] = set()
        for i in value:
            new_value.add(self.sub_conveter(i))
        
        return new_value
    
    def dump(self, value: set) -> tuple:
        return tuple(
            i
            for i in value
        )
    
    def dump_to_jsonable(self, value) -> set: 
        return set(
            self.sub_conveter.dump_to_jsonable(i)
            for i in value
        )
    
    @property
    def type(self): return set


class ListConverter(BaseConverter[typing.List[T]], typing.Generic[T]):

    """列表转换器

    校验内容
    ^^^^^^^^^
    - 是列表
    - 列表元素类型
    - 列表长度
    
    TODO
    - 元素不重复
        - 如果不是简单元素，需要指定标识符获取器
    """

    def __init__(self, 
        element_type: typing.Type[T],
        min_len: Opt[int] = None, max_len: Opt[int] = None,
        mode: ConverterModeT = 'base'
    ):
        super().__init__(mode)

        self.min_len = min_len
        self.max_len = max_len
        converter = get_converter_from_anno(element_type)
        converter.mode = mode
        self.sub_converter: BaseConverter[T] = converter

    def __call__(self, value, **kwargs) -> typing.List[T]:

        # is a list
        if not isinstance(value, list):
            if self.is_base:
                value = list(value)
            
            raise ValueError(f"Value {value} is not list")
        
        # validate length
        length = len(value)
        if self.min_len is not None and length < self.min_len:
            # TODO use (Container)LengthError
            raise ValueError(f'Value {value} is less than minimum length {self.min_len}')
        if self.max_len is not None and length > self.max_len:
            raise ValueError(f'Value {value} is greater than maximum length {self.max_len}')

        # validate element type
        new_value: typing.List[T] = []
        for i in value:
            new_value.append(self.sub_converter(i))
        
        return new_value
    
    @property
    def type(self): return typing.List[self.sub_converter.type]

    def dump_to_jsonable(self, value) -> list:
        return [
            self.sub_converter.dump_to_jsonable(i)
            for i in value
        ]
        

class DatetimeConverter(BaseConverter[datetime.datetime]):

    """日期时间转换器

    是否为 datetime.datetime 对象
    """

    def __call__(self, value, **kwargs) -> datetime.datetime:
        
        if not isinstance(value, datetime.datetime):
            if self.is_base:
                if isinstance(value, str):
                    return datetime.datetime.fromisoformat(value)
                if isinstance(value, (int, float)):
                    return datetime.datetime.fromtimestamp(value)
                
            raise ValueError(f"Value {value} is not datetime.datetime obj")
        
        return value
    
    def dump(self, value) -> str:

        """序列化为 ISO 格式的字符串
        """
        return value.isoformat()
    
    @property
    def type(self): return datetime.datetime

    def dump_to_jsonable(self, value): 
        return value.isoformat()


class TimeConverter(BaseConverter[datetime.time]):

    """时间校验器

    是否为 datetime.time 对象
    """

    def __call__(self, value, **kwargs) -> datetime.time:
        
        if not isinstance(value, datetime.time):
            if self.is_base:
                if isinstance(value, str):
                    return datetime.time.fromisoformat(value)
                
            raise ValueError(f"Value {value} is not datetime.time obj")
        
        return value
    
    def dump(self, value):
        """序列化为 ISO 格式的字符串
        """
        return value.isoformat()
    
    @property
    def type(self): return datetime.time

    def dump_to_jsonable(self, value): 
        return value.isoformat()


class DictConverter(BaseConverter[typing.Dict[typing.Any, T]], typing.Generic[T]):

    """字典校验器

    校验内容
    ^^^^^^^^^
    - 是字典
    - 字典值类型
    """

    def __init__(self, 
        value_type: typing.Type[T],
        mode: ConverterModeT = 'base'
    ):
        
        super().__init__(mode)
        self.value_conveter = get_converter_from_anno(value_type)

    def __call__(self, value, **kwargs) -> typing.Dict[typing.Any, T]:

        # is a dict
        if not isinstance(value, dict):
            if self.is_base:
                value = dict(value)
            
            raise ValueError(f"Value {value} is not dict")
        
        # validate element type
        new_value: typing.Dict[typing.Any, T] = {}
        for k, v in value.items():
            new_value[k] = self.value_conveter(v)
        
        return new_value
    
    @property
    def type(self): 
        return typing.Dict[typing.Any, self.value_conveter.type]
    
    def dump_to_jsonable(self, value) -> dict[str, JsonDumpable]: 
        return {
            str(k): self.value_conveter.dump_to_jsonable(v)
            for k, v in value.items()
        }
