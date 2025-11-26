"""BF Model Converter

数据模型转换器尽可能地保证数据的类型安全、值安全，
常用于数据模型字段中
"""

import abc
import datetime
import typing
import enum
import types
from typing import Optional as Opt

from ..utils.enum_ import load_enum
from .._types import NamedTupleTV, Undefined
from .._types import _undefined
from ..utils.typing_ import JsonDumpable, get_origin, is_json_dumpable, is_namedtuple, safe_issubclass
from ..utils.main import singleton

if typing.TYPE_CHECKING:
    from . import BaseModel

T = typing.TypeVar('T')
ModelTV = typing.TypeVar('ModelTV', bound='BaseModel')
EnumMemberTV = typing.TypeVar('EnumMemberTV', bound=enum.Enum)
ConverterResultTV = typing.TypeVar('ConverterResultTV')
ConverterModeT = typing.Literal['base'] | typing.Literal['strict']
class ConverterProtocol(typing.Protocol):

    def __call__(self, value: typing.Any) -> typing.Any:
        """转换值
        """
        ...


class BaseConverter(typing.Generic[ConverterResultTV], abc.ABC):
    
    """BF Base Converter

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

        If not jsonable, will dump to string.
        """
        if is_json_dumpable(value):
            return value
        else:
            # raise TypeError("cannot dump type %s" % type(value))
            return self.dump_to_str(value)
    

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
    OptionalConverter[str]
    >>> get_converter_from_anno(typing.Optional[str])
    OptionalConverter[str]
    """
    from .main import BaseModel

    ortp = get_origin(tp)
    if safe_issubclass(ortp, BaseModel):
        return ModelConverter(ortp)
    if safe_issubclass(ortp, enum.Enum):
        return EnumConverter(ortp)

    if ortp is int:
        return IntConverter()
    if ortp is float:
        return FloatConverter()
    if ortp is str:
        return StrConverter()
    if ortp is bool:
        return BoolConverter()
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
    if ortp is list:
        tp_args = typing.get_args(tp)
        if len(tp_args) == 0:
            ele_tp = typing.Any
        else:
            ele_tp = tp_args[0]
        return ListConverter(
            element_type=ele_tp
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
            return OptionalConverter(args[1] if args[1] is not types.NoneType else args[0])

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


class ModelConverter(BaseConverter[ModelTV], typing.Generic[ModelTV]):

    """Model Converter for converting data to model instances.
    
    Features
    --------
    Handles serialization (dumping) and deserialization (loading) of model instances.
    Encapsulates all model-level serialization logic including field filtering, 
    flag handling, and format conversion.
    """

    def __init__(self, 
        model_cls: typing.Type[ModelTV],
        mode: ConverterModeT = 'base'
    ) -> None:
        
        super().__init__(mode)
        self.model_cls = model_cls

    def __call__(self, value: dict | ModelTV, **kwargs) -> ModelTV:
        """Load/deserialize value into a model instance.
        
        :param value: 序列化值
        :param kwargs: 额外参数
            - _task_context: 任务上下文
        """
        from . import BaseModel

        if isinstance(value, dict):
            return self.model_cls(**value, **kwargs)
        elif isinstance(value, BaseModel):
            for k, v in kwargs.items():
                value[k] = v
            return value
        else:
            raise ValueError('value should be dict or BaseModel')

    @property
    def type(self): return self.model_cls

    def dump_to_dict(
        self,
        model_instance: ModelTV,
        only_dirty: bool = False,
        exclude_natural_key: bool = False,
        exclude_unset: Opt[bool] = None,
        exclude_flags: Opt[set[str]] = None,
        include_flags: Opt[set[str]] = None,
        only_private: bool = False,
        jsonable: bool = True
    ) -> dict:
        """Serialize model instance to (jsonable) dict.
        
        This method encapsulates all model-level serialization logic,
        handling field filtering, flag-based inclusion/exclusion, and format conversion.

        :param model_instance: The model instance to serialize
        :param only_dirty: 
            If True, only include fields that have been modified.
        :param exclude_natural_key:
            If True, exclude natural key field.
        :param exclude_unset:
            If True, exclude unset fields.
            If None and is partial model, defaults to True.
        :param exclude_flags:
            If provided, exclude fields with all these flags.
            If not provided, ``default_exclude_dump_flags`` configured on
            model will be used.
            Prior to ``include_flags`` (same for model default).
        :param include_flags:
            If provided, only dumps fields with all these flags.
            If not provided, ``default_include_dump_flags`` configured on
            model will be used.
        :param only_private:
            If True, only private fields will be dumped.
        :param jsonable:
            If True, ensure the return is jsonable.

        Behaviour
        ----------
        - Calls each field's converter to serialize field values
        """
        from .field import Field, CompositeField, FieldValueProxy
        
        data = dict()
        field_names: typing.Set[str]

        if only_private:
            field_names = set(model_instance.__private_fields__.keys())
            for k in field_names:
                data[k] = getattr(model_instance, k)
        else:
            if only_dirty:
                field_names = model_instance.__dirty_fields__
            else:
                field_names = set(model_instance.__fields__.keys())

            if exclude_natural_key:
                key_field = model_instance._try_get_key_field()
                if key_field and key_field.is_key_natural():
                    field_names = field_names - {key_field.in_model_name}

            if exclude_unset is True or (exclude_unset is None and model_instance.__partial__):
                field_names = field_names - model_instance.__unset_fields__

            if exclude_flags is None and model_instance.__default_edflags__:
                exclude_flags = model_instance.__default_edflags__

            if include_flags is None and model_instance.__default_idflags__:
                include_flags = model_instance.__default_idflags__

            for k in field_names:
                field: Field = model_instance.__fields__[k]

                # Apply exclude_flags filter
                if exclude_flags:
                    if field.dump_flags.issuperset(exclude_flags):
                        continue

                # Apply include_flags filter (only if exclude_flags is not provided or empty)
                # This ensures exclude_flags has priority over include_flags
                if include_flags and not exclude_flags:
                    if not field.dump_flags.issuperset(include_flags):
                        continue

                field_v = FieldValueProxy.dump(getattr(model_instance, k))
                if jsonable:
                    if isinstance(field, CompositeField):
                        data.update(field.dump_val_to_jsonable(field_v))
                    else:
                        data[k] = field.dump_val_to_jsonable(field_v)
                else:
                    data[k] = field_v

        return data
    
    def dump_to_str(
        self,
        model_instance: ModelTV,
        use_name: bool = False
    ) -> str:
        """Serialize model instance to string.
        
        :param model_instance: The model instance to serialize
        :param use_name: use field's name instead of in_model_name,
                        defaults to False
        """
        from .field import FieldValueProxy
        
        parts = []
        for in_name, field in model_instance.__fields__.items():
            field_name = field.name if use_name else in_name
            field_value = FieldValueProxy.dump(model_instance[field])
            dumped_value = field.dump_val_to_str(field_value)
            parts.append(f"{field_name}={dumped_value}")
        
        return ",".join(parts)

    def dump_to_jsonable(self, value): 
        """Serialize model instance to jsonable dict.
        
        This is the method called by BaseConverter for standard serialization.
        It delegates to dump_to_dict with jsonable=True.
        """
        return self.dump_to_dict(value, jsonable=True)


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
        return load_enum(self.enum_cls, value)
    
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

class OptionalConverter(BaseConverter[typing.Optional[ConverterResultTV]]):

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
        else:
            self.sub_converter = tp_converter

    def __call__(self, value, **kwargs) -> ConverterResultTV | types.NoneType:
        
        try:
            NoneConverter()(value)
        except ValueError:
            return self.sub_converter(value)
        
    @property
    def type(self): return typing.Type[typing.Optional[self.sub_converter.type]]

    def dump_to_jsonable(self, value: ConverterResultTV) -> JsonDumpable:
        if value is None:
            return None
        else:
            return self.sub_converter.dump_to_jsonable(value)


class BoolConverter(BaseConverter[bool]):
    """Boolean Converter"""

    def __call__(self, value: typing.Any, **kwargs) -> bool:
        if isinstance(value, bool):
            return value
        if self.is_base:
            if isinstance(value, str):
                if value.lower() in ('true', '1', 'yes', 'on'):
                    return True
                if value.lower() in ('false', '0', 'no', 'off'):
                    return False
            if isinstance(value, int):
                return bool(value)
        raise ValueError(f'Value {value} is not a boolean')
    
    @property
    def type(self): return bool


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

        self._sub_converters: tuple[BaseConverter, ...]
        tuple_type_args = typing.get_args(tuple_type)
        if len(tuple_type_args) > 1 and tuple_type_args[1] == Ellipsis:
            self._only_a_type = True
            self._sub_converters = (get_converter_from_anno(tuple_type_args[0]),)
        else:
            self._only_a_type = False
            self._sub_converters = tuple(
                get_converter_from_anno(type_)
                for type_ in tuple_type_args
            )

    def __call__(self, value, **kwargs) -> tuple[typing.Unpack[TupleValueTV]]:
        
        if not isinstance(value, tuple):
            if self.is_base:
                value = tuple(value)

        if not self._only_a_type:
            if len(value) != len(self._sub_converters):
                raise ValueError(f'Value {value} is not a tuple of length {len(self._sub_converters)}')
        
            return tuple(
                validator(value[i])
                for i, validator in enumerate(self._sub_converters)
            )
        else:
            return tuple(
                self._sub_converters[0](i)
                for i in value
            )
    
    @property
    def type(self): return typing.Tuple[*tuple(
        validator.type 
        for validator in self._sub_converters
    )]

    def dump_to_jsonable(self, value) -> tuple:
        if not self._only_a_type:
            return tuple(
                self._sub_converters[i].dump_to_jsonable(value[i])
                for i in range(len(value))
            )
        else:
            return tuple(
                self._sub_converters[0].dump_to_jsonable(i)
                for i in value
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
            else:
                raise ValueError(f"Value {value} is not a set")
        
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
        return value.isoformat()

    def dump_to_jsonable(self, value):
        return value.isoformat()
    
    @property
    def type(self): return datetime.datetime


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
