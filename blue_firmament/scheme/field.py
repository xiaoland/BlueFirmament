"""
Module of Scheme.Field


References
----------
- `issue#7 <https://github.com/xiaoland/BlueFirmament/issues/7>`_
"""


import functools
import typing

from .validator import BaseValidator, get_validator_by_type

if typing.TYPE_CHECKING:
    from .main import BaseScheme


class UndefinedValue:

    """未定义值
    """
    
    def __repr__(self):
        return 'BlueFirmamentUndefinedValue'
    
    @classmethod
    def is_(cls, value: typing.Any) -> typing.TypeGuard['UndefinedValue']:
        """判断值是否为未定义值

        value 是 UndefineValue 或 UndefinedValue 的实例都被视为未定义值
        """
        return value is cls or isinstance(value, cls)
    
    def __bool__(self) -> bool:
        return False
    
    def __hash__(self) -> int:
        return hash('BlueFirmamentUndefinedValue')


FieldValueType = typing.TypeVar('FieldValueType')
class FieldValueProxy(typing.Generic[FieldValueType]):

    '''
    字段值代理对象

    字段值必然是原生值，不能是用户自定义类

    - 检测对可变对象的修改
    - 获得所属的字段实例
    ''' 

    def __init__(self, 
        obj: FieldValueType, 
        modified: typing.Callable,
        field: "BlueFirmamentField[FieldValueType]",
        scheme: "BaseScheme"
    ) -> None:

        self._obj: FieldValueType = obj
        self._modified = modified
        self._field: "BlueFirmamentField[FieldValueType]" = field
        self._scheme: "BaseScheme" = scheme

    @property
    def scheme(self): return self._scheme
    
    @property
    def field(self): return self._field

    @property
    def obj(self) -> FieldValueType:
        """获取原始对象

        这个对象是不可变的
        """
        return self._obj

    @staticmethod
    def _get_obj_dunder_method_caller(name: str) -> typing.Callable:

        def dunder_method_caller(self: typing.Self, *args, **kwargs):
            return getattr(self._obj, name)(*args, **kwargs)

        return dunder_method_caller

    def __getattr__(self, name: str) -> typing.Any:
        
        attr = getattr(self._obj, name)
        
        # 代理方法
        if callable(attr):
            @functools.wraps(attr)
            def wrapper(*args, **kwargs):
                res = attr(*args, **kwargs)
                self._modified()  # 字段内部修改
                # TODO 并不是所有方法都会导致值的修改，这也没办法
                return res
            return wrapper

        return attr
    
    def __setattr__(self, name: str, value: typing.Any) -> None:
        
        if name in ('_obj', '_modified', '_field', '_scheme'):
            super().__setattr__(name, value)
        else:
            setattr(self._obj, name, value)

    @staticmethod
    def dump(value: FieldValueType | "FieldValueProxy[FieldValueType]") -> FieldValueType:
        if isinstance(value, FieldValueProxy):
            return value.obj
        return value


for i in (
    'add', 'sub', 'mul', 'truediv', 'floordiv', 'mod', 'pow',
    'eq', 'ne', 'lt', 'le', 'gt', 'ge',
    'len', 'getitem', 'setitem', 'contains',
    'int', 'float', 'str', 'repr',
    'bool', 'hash', 'call', 'iter',
    'next', 'reversed', 'abs', 'round',
    'and', 'or', 'xor', 'invert',
    'lshift', 'rshift'
):
    setattr(
        FieldValueProxy, f'__{i}__', 
        FieldValueProxy._get_obj_dunder_method_caller(f'__{i}__')
    )

@typing.runtime_checkable
class FieldValueProtocol(typing.Protocol[FieldValueType]):

    __field__: "BlueFirmamentField[FieldValueType]"
    __scheme__: "BaseScheme"


class BlueFirmamentField(typing.Generic[FieldValueType]):

    """碧霄数据模型字段

    在定义数据模型时使用

    Features
    --------
    - 基于字段构建适用于数据访问层的筛选器
    - 使用定义的校验器校验字段值
    - 使用定义的序列化器序列化字段值
    """

    __origin__: FieldValueType

    def __init__(
        self, 
        default: UndefinedValue | FieldValueType = UndefinedValue(), 
        default_factory: typing.Optional[typing.Callable[[], FieldValueType]] = None,
        name: typing.Optional[str] = None,
        in_scheme_name: typing.Optional[str] = None,
        scheme_cls: typing.Optional[typing.Type["BaseScheme"]] = None,
        is_primary_key: bool = False,
        converter: typing.Optional[typing.Callable[[typing.Any], FieldValueType]] = None,
        vtype: UndefinedValue | typing.Type[FieldValueType] = UndefinedValue()
    ):

        """
        Parameters
        ^^^
        - `default`: 默认值；初始化时若未提供该字段的值则使用此默认值；实例化之后不可修改
        - `name`：字段名；与数据访问层交互该字段时使用该名称；实例化之后不可修改
        - `in_scheme_name`：在数据模型中的名称；默认与 `name` 相同；实例化之后不可修改
        - `scheme`：数据模型；该字段所属的数据模型类；实例化设置后不可修改
        - `default_factory`：默认值工厂；默认值需要动态生成或者为可变对象时使用，应该是一个可调用对象
        - `is_primary_key`：是否为主键；默认为假
        - `converter`：校验器；数据模型将用此校验字段值
        - `vtype`：字段值类型；如果提供，基于此设置校验器（ ``converter`` 优先）
        """
        self.__name = name
        self.__in_scheme_name = in_scheme_name or name
        self.__scheme_cls = scheme_cls
        self.__default = default
        self.__default_factory = default_factory
        self.__is_primary_key = is_primary_key
        self.__validator = converter or get_validator_by_type(vtype)
        if not isinstance(vtype, UndefinedValue):
            self.__origin__ = vtype

    @property
    def vtype(self):
        return self.__origin__
        
    def fork(self, 
        default: UndefinedValue | FieldValueType = UndefinedValue(),
        default_factory: typing.Optional[typing.Callable[[], FieldValueType]] = None,
        name: typing.Optional[str] = None,
        in_scheme_name: typing.Optional[str] = None,
        scheme_cls: typing.Optional[typing.Type["BaseScheme"]] = None,
        is_primary_key: bool = False,
        validator: typing.Optional[typing.Callable[[typing.Any], FieldValueType]] = None,
        vtype: UndefinedValue | typing.Type[FieldValueType] = UndefinedValue()
    ) -> typing.Self:

        """克隆字段实例
        """
        return self.__class__(
            default=default if not UndefinedValue.is_(default) else self.__default,
            default_factory=default_factory or self.__default_factory,
            name=name or self.__name,
            in_scheme_name=in_scheme_name or self.__in_scheme_name,
            scheme_cls=scheme_cls or self.__scheme_cls,
            is_primary_key=is_primary_key or self.__is_primary_key,
            converter=validator or self.__validator,
            vtype=vtype if not UndefinedValue.is_(vtype) else self.__origin__,
        )
    
    def __hash__(self) -> int:
        """哈希值

        in_scheme_name or name
        """
        return hash(self.__in_scheme_name or self.__name)
    
    def __eq__(self, value) -> bool:

        """
        Make BlueFirmamentField(name='name') == 'name'
        """
        if isinstance(value, str):
            return self.__name == value or self.__in_scheme_name == value
        elif isinstance(value, BlueFirmamentField):
            # name, vtype
            return self.__name == value.name and self.vtype == value.vtype
        return False

    @property
    def name(self) -> str: 
        if self.__name is None:
            raise ValueError('Field name is not defined')
        return self.__name
    
    @property
    def in_scheme_name(self) -> str:
        if self.__in_scheme_name is None:
            raise ValueError('Field in_scheme_name is not defined')
        return self.__in_scheme_name

    def _set_name(self, value: str, no_raise: bool = False) -> None:
        """设置字段名称

        如果已经设置过名称，则抛出错误；如果不想抛出错误，则传入 ``no_raise`` 参数为 ``True``
        """
        if self.__name is not None:
            if no_raise:
                return None
            raise ValueError('Field name is immutable')
        self.__name = value

    def _set_in_scheme_name(self, value: str, no_raise: bool = False) -> None:
        """设置字段在数据模型中的名称

        如果已经设置过名称，则抛出错误
        """
        if self.__in_scheme_name is not None:
            if no_raise:
                return None
            raise ValueError('Field in_scheme_name is immutable')
        self.__in_scheme_name = value

    @property
    def is_primary_key(self) -> bool: return self.__is_primary_key

    def set_validator_from_type(self, annotation: FieldValueType):

        """从类型注解设置校验器
        """
        self.__origin__ = annotation
        self.__validator = get_validator_by_type(annotation)

    def dump_to_json(self) -> str:

        """
        序列化为JSON
        """
        return '' # TODO

    def dump_to_primitive(self):

        """
        序列化为Python原生类型
        """
        pass # TODO

    def validate(self, value: typing.Any) -> FieldValueType:

        """校验字段值

        返回处理后的值（如果无法处理会抛出错误）；没有定义校验器则直接返回值
        """
        if self.__validator:
            return self.__validator(value)
        else:
            return value

    @property
    def default_value(self) -> FieldValueType:

        """默认值

        Behavior
        ---------
        - 默认值工厂优先于默认值
        - 都未提供则抛出 ``ValueError``
        """
        if self.__default_factory:
            return self.__default_factory()
        elif not isinstance(self.__default, UndefinedValue) or self.__default is UndefinedValue: # why type guard not work
            return self.__default
        else:
            raise ValueError('No default value provided for field')

    @typing.overload
    def __get__(self, instance: None, owner) -> typing.Self:
        ...

    @typing.overload
    def __get__(self, instance: "BaseScheme", owner) -> FieldValueType:
        # 实际上是 FieldValueProxy[FieldValueType]
        ...
    
    def __get__(self, instance: typing.Optional["BaseScheme"], owner) \
        -> "BlueFirmamentField" | FieldValueType:

        if instance is None:
            return self
        return typing.cast(FieldValueType, instance.get_value(self))
        
    def __set__(self, instance: "BaseScheme", value: FieldValueType) -> None:

        initialized = self.in_scheme_name in instance.__field_values__

        if UndefinedValue.is_(value):
            value = self.default_value
        else:
            value = self.validate(value)

        if instance.__proxy__:
            value_ = self._proxy_value(value, instance)
        else:
            value_ = value

        # proxy value by override __getattribute__
        # if not initialized:
        #     if is_mutable(value):
        #         setattr(value, '__getattribute__', 
        #             FieldValueProxy.__getattr__
        #         )

        # add scheme, field info on value
        # if not initialized:
        #     setattr(value, '__scheme__', instance)
        #     setattr(value, '__field__', self)
        
        instance.set_value(self, value_)  # save

        # if already initialized, mark as dirty
        if initialized:
            instance.mark_dirty(self.in_scheme_name)

    def _proxy_value(self, 
        value: FieldValueType, instance: "BaseScheme"
    ) -> FieldValueProxy[FieldValueType]:
        
        if not isinstance(value, FieldValueProxy):
            # 避免循环代理
            return FieldValueProxy(
                value, 
                lambda: instance.mark_dirty(self.in_scheme_name),
                self,
                instance
            )
        return value  # 已经是代理对象了



T = typing.TypeVar('T')
def Field(
    default: T | UndefinedValue = UndefinedValue(), 
    default_factory: typing.Optional[typing.Callable[[], T]] = None,
    name: typing.Optional[str] = None,
    is_primary_key: bool = False,
    converter: typing.Optional[BaseValidator] = None,
    vtype: UndefinedValue | typing.Type[T] = UndefinedValue()
):
    
    return BlueFirmamentField[T](
        default=default, 
        default_factory=default_factory, 
        name=name, 
        is_primary_key=is_primary_key, 
        converter=converter,
        vtype=vtype
    )

class BlueFirmamentPrivateField[FieldValueType](BlueFirmamentField[FieldValueType]):

    """碧霄私有字段

    - 不会被外部访问？（setting 那边的实践有问题）
    - 不会被序列化
    - 不会与数据访问层交互
    """
    
    @property
    def name(self) -> str:
        raise ValueError('Private field name is forbidden')


def PrivateField(
    default: T | UndefinedValue = UndefinedValue(),
    default_factory: typing.Optional[typing.Callable[[], T]] = None,
    name: typing.Optional[str] = None,
    is_primary_key: bool = False,
    converter: typing.Optional[BaseValidator] = None,
    vtype: typing.Type[T] | UndefinedValue = UndefinedValue()
):
    
    return BlueFirmamentPrivateField(
        default=default, 
        default_factory=default_factory, 
        name=name, 
        is_primary_key=is_primary_key, 
        converter=converter,
        vtype=vtype
    )


def field_as_class_var(field: BlueFirmamentField[T]) -> T:

    '''将字段当作类变量使用

    传入字段实例，返回字段实例的默认值
    '''
    return typing.cast(BlueFirmamentField[T], field).default_value

def dump_field_name(field: BlueFirmamentField | str) -> str:

    if isinstance(field, BlueFirmamentField):
        return field.name
    return field
