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

from ..utils.type import get_origin, is_annotated, safe_issubclass
from ..utils import singleton

if typing.TYPE_CHECKING:
    from . import SchemeTV, BaseScheme
    from .enum import EnumClassTV, EnumMemberTV


T = typing.TypeVar('T')
ConverterResultTV = typing.TypeVar('ConverterResultTV')
ConverterModeT = typing.Literal['base'] | typing.Literal['strict']
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
    def __call__(self, value) -> ConverterResultTV:
        """转换值
        """
        raise NotImplementedError('`__call__` method must be implemented in subclass')
    
    def dump(self, value: ConverterResultTV) -> typing.Any:

        """序列化值
        """
        return value
    

def get_converter_from_anno(
    tp: typing.Type
) -> BaseConverter:
    
    """根据类型注释获取转换器

    Behaviour
    ---------
    - 找不到合适的校验器则返回通用校验器 :class:`AnyConverter`
    - 支持枚举、数据模型
    - 支持 NewType, UnionType, Annotated, Optional

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

    # parse union type and optional type
    if typing.get_origin(tp) is typing.Union:
        args = typing.get_args(tp)
        # if only two and one is None, it's optional
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
    
    def __call__(self, value: typing.Any) -> typing.Any: 
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

    def __call__(self, *args, **kwargs) -> SchemeTV:
        return self.scheme_cls(*args, **kwargs)

    @property
    def type(self): return self.scheme_cls


class EnumConverter(BaseConverter[EnumMemberTV], typing.Generic[EnumMemberTV]):

    """枚举转换器
    """

    def __init__(self, 
        enum_cls: typing.Type[EnumMemberTV],
        mode: ConverterModeT = 'base'
    ) -> None:
        
        super().__init__(mode)
        self.enum_cls = enum_cls

    def __call__(self, value) -> EnumMemberTV:
        return self.enum_cls(value)
    
    @property
    def type(self): return self.enum_cls


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

    def __call__(self, value: typing.Any) -> typing.Any:

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
        tp: typing.Type[ConverterResultTV],
        mode: ConverterModeT = 'base'
    ):
        super().__init__(mode)

        self.sub_converter = get_converter_from_anno(tp)

    def __call__(self, value) -> ConverterResultTV | types.NoneType:
        
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
        min: Opt[int] = None, max: Opt[int] = None,
        mode: ConverterModeT = 'base'
    ):
        
        super().__init__(mode)

        self.min = min
        self.max = max

    def __call__(self, value: typing.Any) -> int:
        
        res = int(value)
        if self.min is not None and res < self.min:
            raise ValueError(f'Value {res} is less than minimum {self.min}')
        if self.max is not None and res > self.max:
            raise ValueError(f'Value {res} is greater than maximum {self.max}')
        return res
    
    @property
    def type(self): return int
    

class StrConverter(BaseConverter[str]):

    """字符串转换器
    """

    def __init__(self, 
        min: Opt[int] = None, max: Opt[int] = None,
        allow_empty: bool = False,
        mode: ConverterModeT = 'base'
    ):
        super().__init__(mode)

        self.min_len = min
        self.max_len = max
        self.allow_empty = allow_empty

    def __call__(self, value) -> str:
        
        res = ''
        if self.is_base:
            res = str(value)
        if self.is_strict:
            if not isinstance(value, str):
                raise ValueError(f'Value {value} is not str')
            res = value

        length = len(res)
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

    def __call__(self, value: typing.Any) -> None:

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


TupleTV = typing.TypeVar('TupleTV', bound=tuple)
class TupleConverter(BaseConverter[TupleTV], typing.Generic[TupleTV]):

    """元组转换器

    按照顺序校验每个元素的值，长度必须一致
    """

    def __init__(self, 
        tuple_type: TupleTV,
        mode: ConverterModeT = 'base'
    ):
        super().__init__(mode)
        
        self.sub_converters: typing.Tuple[BaseConverter] = tuple(
            get_converter_from_anno(type_)  # TODO inherit mode
            for type_ in tuple_type
        )

    def __call__(self, value) -> TupleTV:
        
        if not isinstance(value, tuple):
            if self.is_base:
                value = tuple(value)

        if len(value) != len(self.sub_converters):
            raise ValueError(f'Value {value} is not a tuple of length {len(self.sub_converters)}')
        
        return typing.cast(TupleTV, tuple(
            validator(value[i]) 
            for i, validator in enumerate(self.sub_converters)
        ))
    
    @property
    def type(self): return typing.Tuple[*tuple(
        validator.type 
        for validator in self.sub_converters
    )]
    


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
        self.sub_validator: BaseConverter[T] = get_converter_from_anno(element_type)

    def __call__(self, value) -> set:
        
        # is a set
        if not isinstance(value, set):
            if self.is_base:
                value = set(value)
            
            raise ValueError(f"Value {value} is not set")
        
        # validate element type
        new_value: typing.Set[T] = set()
        for i in value:
            new_value.add(self.sub_validator(i))
        
        return new_value
    
    def dump(self, value: set) -> tuple:
        
        return tuple(
            i
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

    def __call__(self, value) -> typing.List[T]:

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
        

class DatetimeConverter(BaseConverter[datetime.datetime]):

    """日期时间转换器

    是否为 datetime.datetime 对象
    """

    def __call__(self, value) -> datetime.datetime:
        
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


class TimeConverter(BaseConverter[datetime.time]):

    """时间校验器

    是否为 datetime.time 对象
    """

    def __call__(self, value) -> datetime.time:
        
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
        self.value_validator = get_converter_from_anno(value_type)

    def __call__(self, value) -> typing.Dict[typing.Any, T]:

        # is a dict
        if not isinstance(value, dict):
            if self.is_base:
                value = dict(value)
            
            raise ValueError(f"Value {value} is not dict")
        
        # validate element type
        new_value: typing.Dict[typing.Any, T] = {}
        for k, v in value.items():
            new_value[k] = self.value_validator(v)
        
        return new_value
