"""BlueFirmament Scheme Field module
"""

__all__ = [
    "FieldValueProxy",
    "Field",
    "PrivateField",
    "FieldTV",
    "CompositeField",
    "field",
    "private_field",
    "get_default",
    "dump_field_name",
]

import functools
import typing
from typing import Optional as Opt
from .._types import Undefined, _undefined
from ..utils.type import safe_issubclass
from ..dal.filters import (
    ContainsFilter, EqFilter, NotEqFilter,
    InFilter, OrderModifier, NotFilter
)
from .converter import BaseConverter, get_converter_from_anno

if typing.TYPE_CHECKING:
    from .main import BaseScheme
    from .validator import BaseValidator


FieldValueTV = typing.TypeVar('FieldValueTV')
class FieldValueProxy(typing.Generic[FieldValueTV]):

    '''
    字段值代理对象

    字段值必然是原生值，不能是用户自定义类

    - 检测对可变对象的修改
    - 获得所属的字段实例

    Implementation
    --------------
    透明代理
    ^^^^^^^^^^
    - 在下方通过 for 循环注册了一堆特殊方法
    - `__bool__` 特殊处理
    ''' 

    def __init__(self, 
        obj: FieldValueTV, 
        modified: typing.Callable,
        field: "Field[FieldValueTV]",
        scheme: "BaseScheme"
    ) -> None:

        self._obj: FieldValueTV = obj
        self._modified = modified
        self._field: "Field[FieldValueTV]" = field
        self._scheme: "BaseScheme" = scheme

    @property
    def scheme(self): return self._scheme
    
    @property
    def field(self): return self._field

    @property
    def obj(self) -> FieldValueTV:
        """获取原始对象

        这个对象是不可变的
        """
        return self._obj

    @staticmethod
    def _get_obj_dunder_method_caller(name: str) -> typing.Callable:

        def dunder_method_caller(self: typing.Self, *args, **kwargs):
            return getattr(self._obj, name)(*args, **kwargs)

        return dunder_method_caller

    def __bool__(self):

        try:
            return getattr(self._obj, '__bool__')()
        except AttributeError:
            return bool(self._obj)

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
    def dump(value: FieldValueTV | "FieldValueProxy[FieldValueTV]") -> FieldValueTV:
        if isinstance(value, FieldValueProxy):
            return value.obj
        return value


for i in (
    'add', 'sub', 'mul', 'truediv', 'floordiv', 'mod', 'pow',
    'eq', 'ne', 'lt', 'le', 'gt', 'ge',
    'len', 'getitem', 'setitem', 'contains',
    'int', 'float', 'str', 'repr',
    'hash', 'call', 'iter',
    'next', 'reversed', 'abs', 'round',
    'and', 'or', 'xor', 'invert',
    'lshift', 'rshift'
):
    setattr(
        FieldValueProxy, f'__{i}__', 
        FieldValueProxy._get_obj_dunder_method_caller(f'__{i}__')
    )

@typing.runtime_checkable
class FieldValueProtocol(typing.Protocol[FieldValueTV]):

    __field__: "Field[FieldValueTV]"
    __scheme__: "BaseScheme"


class Field(typing.Generic[FieldValueTV]):

    """Scheme Field of BlueFirmament.

    Features
    --------
    Get DAL Filter
    ^^^^^^^^^^^^^^
    >>> Field[int](name='_id').equals(1)
    EqFilter(field='_id', value=1)

    Validator
    ^^^^^^^^^
    See :doc:`/design/scheme/validator`
    """

    def __init__(
        self, 
        default: typing.Union[Undefined, FieldValueTV] = _undefined, 
        default_factory: Opt[typing.Callable[[], FieldValueTV]] = None,
        vtype: Undefined | typing.Type[FieldValueTV] = _undefined,
        name: Opt[str] = None,
        in_scheme_name: Opt[str] = None,
        scheme_cls: Opt[typing.Type["BaseScheme"]] = None,
        is_key: bool = False,
        is_natural_key: bool = True,
        is_foreign_key: bool = False,
        converter: Opt[BaseConverter[FieldValueTV]] = None,
        validators: Opt[typing.Iterable["BaseValidator"]] = None,
        is_partial: bool = False,
        dump_flags: Opt[set[str]] = None,
        init: bool = True,
    ):

        """
        :param default:
            Immutable value used when set value not provided(``_undefined``).
        :param default_factory:
            Callable to get mutable value as default value.
        :param vtype: 
            Field value type.
        :param name:
            Field name in DAL.
        :param in_scheme_name:
            Field name in scheme.
        :param scheme_cls:
            Scheme class this field attached on.
        :param converter:
            See :doc:`/design/scheme/converter`
        :param validators:
            See :doc:`/design/scheme/validator`
        :param is_partial:
            If True, field value left undefined if not provided, and
            default value will not be applied.
        :param dump_flags:
            Flags control whether this field should be dumped when
            dumping scheme.
        :param is_key: 
            This field is a key
        :param is_natural_key:
            If this field is a key, it is managed by DataSource (False for surrogate)
        :param is_foreign_key:
            If you want to mark a primary or composite key, use KeyField instead
        :param init: 
            see `Dataclass field specifier parameters <https://typing.python.org/en/latest/spec/dataclasses.html#field-specifier-parameters>`_
        """
        self.__name = name
        self.__in_scheme_name = in_scheme_name or name
        self.__scheme_cls = scheme_cls
        self.__default = default
        self.__default_factory = default_factory
        self.__vtype = vtype
        self.__is_key = is_key
        self.__is_natural_key = is_natural_key
        self.__is_foreign_key = is_foreign_key
        self.__converter: BaseConverter | None = converter
        self.__validators: typing.List["BaseValidator"] = list(validators or [])
        self.__is_partial = is_partial
        self.__dump_flags = dump_flags or set()
        self.__init = init
        
    def fork(self, 
        default: Undefined | FieldValueTV = _undefined,
        default_factory: Opt[typing.Callable[[], FieldValueTV]] = None,
        vtype: Undefined | typing.Type[FieldValueTV] = _undefined,
        name: Opt[str] = None,
        in_scheme_name: Opt[str] = None,
        scheme_cls: Opt[typing.Type["BaseScheme"]] = None,
        is_key: bool = False,
        is_natural_key: bool = True,
        is_foreign_key: bool = False,
        converter: Opt[BaseConverter[FieldValueTV]] = None,
        fork_validators: bool = True,
        is_partial: Opt[bool] = None,
        dump_flags: Opt[set[str]] = None,
        init: Opt[bool] = None,
    ) -> typing.Self:
        try:
            return self.__class__(
                default=default if default is not _undefined else self.__default,
                default_factory=default_factory or self.__default_factory,
                name=name or self.__name,
                in_scheme_name=in_scheme_name or self.__in_scheme_name,
                scheme_cls=scheme_cls or self.__scheme_cls,
                is_key = is_key or self.__is_key,
                is_natural_key = is_natural_key or self.__is_natural_key,
                is_foreign_key=is_foreign_key or self.__is_foreign_key,
                converter=converter or self.__converter,
                validators=self.__validators if fork_validators else None,
                is_partial=is_partial or self.__is_partial,
                dump_flags=dump_flags or self.__dump_flags,
                init=init or self.__init,
                vtype=vtype if vtype is not _undefined else self.__vtype
            )
        except TypeError:
            # customized no-parameter field
            return self.__class__()
    
    def __hash__(self) -> int:
        """哈希值

        in_scheme_name or name
        """
        return hash(self.__in_scheme_name or self.__name)
    
    def __eq__(self, value) -> bool:

        """Make BlueFirmamentField(name='name') == 'name'
        """
        if isinstance(value, str):
            return self.__name == value or self.__in_scheme_name == value
        elif isinstance(value, Field):
            # name, vtype
            return self.__name == value.name and self.value_type == value.value_type
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
    
    def is_key(self) -> bool: 
        return self.__is_key
    def is_natural_key(self) -> bool:
        return self.__is_natural_key

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
    def vtype(self) -> typing.Type[FieldValueTV]:
        if self.__vtype is _undefined:
            raise ValueError(f"vtype is not set on field {self.name}")
        return self.__vtype
    
    @property
    def is_partial(self) -> bool:
        return self.__is_partial

    @property
    def scheme_cls(self) -> typing.Type["BaseScheme"]: 
        if self.__scheme_cls is None:
            raise ValueError('Field scheme is not defined')
        return self.__scheme_cls
    
    @property
    def dump_flags(self) -> set[str]:
        return self.__dump_flags

    def _set_scheme_cls(self, 
        scheme_cls: Opt[typing.Type["BaseScheme"]],
        no_raise: bool = False,
        force: bool = False
    ) -> None:
        """设置字段所属的数据模型

        如果已经设置过数据模型，则抛出错误

        :param force: 是否强制设置 \n
            建议使用 :meth:`fork` 来设置值（但元类是特例）
        """
        if self.__scheme_cls is not None and not force:
            if no_raise: return None
            raise ValueError('Field scheme is immutable')
        self.__scheme_cls = scheme_cls

    @property
    def init(self) -> bool: return self.__init

    def _set_converter(self, 
        converter: BaseConverter[FieldValueTV],
        safe: bool = True
    ) -> None:

        """
        :param converter:

        :raise ValueError: Conveter has been set
        """
        if self.__converter is not None:
            if not safe:
                raise ValueError('converter is immutable')
            else:
                return
        self.__converter = converter

    def _set_converter_from_anno(self, 
        annotation: typing.Type[FieldValueTV],
        safe: bool = True
    ) -> None:

        """从类型注解设置转换器

        - 支持 `BlueFirmamentField[type]`
        - 支持 `BlueFirmamentFieldSublcass` （必须是直接子类，不能是孙类）
        - 用户不应当调用

        :param annotation: 类型注解
        :param safe: 已经设置时是否不报错
        :raise ValueError: 如果已经设置过转换器
        """
        if self.__converter is not None:
            if not safe:
                raise ValueError('converter is immutable')
            else:
                return

        if typing.get_origin(annotation) is self.__class__:
            annotation = typing.get_args(annotation)[0]
        else:
            if safe_issubclass(annotation, Field):
                annotation = annotation.__orig_bases__[0]  # type: ignore[attr-defined]

        self.__converter = get_converter_from_anno(annotation)

    def _add_validator(self, validator: "BaseValidator") -> None:

        """添加校验器

        :param validator: 校验器

        - 用户不应当调用
        """
        self.__validators.append(validator)

    @property
    def value_type(self) -> typing.Type[FieldValueTV]:
        
        """获取字段值类型

        从校验器中获取
        """
        if self.__converter:
            return self.__converter.type
        else:
            raise ValueError('Field value type is not defined')
    
    def dump_val_to_str(self, value: FieldValueTV):
        """Dump field value to string
        """
        if value is not _undefined:
            return self.converter.dump_to_str(value)
        else:
            return _undefined.value

    def dump_val_to_jsonable(self, value: FieldValueTV):

        """Dump field value to jsonable types
        """
        if value is not _undefined:
            return self.converter.dump_to_jsonable(value)
        else:
            return _undefined.value

    @property
    def converter(self) -> BaseConverter:
        if self.__converter is None:
            raise ValueError('converter is not defined on field %s' % self.in_scheme_name)
        return self.__converter

    @property
    def default_value(self) -> FieldValueTV:

        """默认值

        - 默认值工厂优先于默认值

        :raise ValueError: If no default value provided.
        """
        if self.__default_factory:
            return self.__default_factory()
        elif self.__default is not _undefined:
            return self.__default
        else:
            raise ValueError('No default value provided for field %s' % self.in_scheme_name)
    
    def convert(self, value: typing.Any) -> FieldValueTV:

        """转换字段值

        返回转换后的值（如果无法处理会抛出错误）；
        没有定义转换器则直接返回值
        """
        if self.__converter:
            return self.__converter(value)
        else:
            return value
        
    def validate(self, 
        value: typing.Any,
        scheme_ins: Opt["BaseScheme"] = None
    ) -> None:

        """校验字段值

        :raises ValueError: 如果值不合法
        """
        for validator in self.__validators:
            validator(value, scheme_ins=scheme_ins)
        
    def equals(self, value: typing.Any) -> EqFilter:
        '''该字段等于该值的筛选器
        '''
        return EqFilter(self, value)
    
    def contains(self, *value: typing.Any) -> ContainsFilter:

        """该字段包含所有元素的筛选器
        """
        return ContainsFilter(self, *value)
    
    def not_equals(self, value: typing.Any) -> NotEqFilter:
        """该字段不等于该值的筛选器
        """
        return NotEqFilter(self, value)
    
    def in_(self, value: typing.Iterable[typing.Any]) -> InFilter:
        """该字段在该列表中的筛选器
        """
        return InFilter(self, value)
    
    def not_in_(self, value: typing.Iterable[typing.Any]) -> tuple[NotFilter, InFilter]:
        return (NotFilter(), self.in_(value))
    
    def order_by(self, *, desc: bool = False) -> OrderModifier:

        """按该字段进行排序的修改器
        """
        return OrderModifier(self, desc=desc)

    @typing.overload
    def __get__(self, instance: None, owner) -> typing.Self:
        ...

    @typing.overload
    def __get__(self, instance: "BaseScheme", owner) -> FieldValueTV:
        # 实际上是 FieldValueProxy[FieldValueType]
        ...
    
    def __get__(self, instance: Opt["BaseScheme"], owner) \
        -> "Field" | FieldValueTV:

        if instance is None:
            return self
        return typing.cast(FieldValueTV, instance._get_value(self))
        
    def __set__(self, instance: "BaseScheme", value: FieldValueTV) -> None:

        """
        .. versionchanged:: 0.1.2
            if initialized, set to undefined will change nothing
        """

        initialized = self.in_scheme_name in instance.__field_values__

        # convert value
        if value is _undefined:
            if initialized:
                return  # remain value unchanged

            instance._mark_unset(self.in_scheme_name)
            try:
                value = self.default_value
            except ValueError as e:
                if self.__is_partial or instance.__partial__:
                    instance._set_value(self, _undefined)
                    return
                else:
                    raise e
        else:
            value = self.convert(value)

        # validate value
        self.validate(value, scheme_ins=instance)

        if instance.__proxy__:
            value_ = self._proxy_value(value, instance)
        else:
            value_ = value
        
        instance._set_value(self, value_)  # save

        # if already initialized, mark as dirty
        if initialized:
            instance._mark_dirty(self.in_scheme_name)

    def _proxy_value(self, 
        value: FieldValueTV, instance: "BaseScheme"
    ) -> FieldValueProxy[FieldValueTV]:
        
        if not isinstance(value, FieldValueProxy):
            # 避免循环代理
            return FieldValueProxy(
                value, 
                lambda: instance._mark_dirty(self.in_scheme_name),
                self,
                instance
            )
        return value  # 已经是代理对象了

    def dump_to_dict(self, value: FieldValueTV) -> dict[str, FieldValueTV]:

        """获取字段及其值组成的字典

        :param value: 字段值；会先由校验器处理
        """
        return {
            self.name: self.convert(value)
        }

    def dump_to_scheme(self) -> typing.Type["BaseScheme"]:

        """
        根据字段实例创建数据模型

        这个数据模型只包含本字段
        """

        exec_namespace = {
            "BaseScheme": BaseScheme,
            "FieldIns": self,
        }
        exec_result = {}

        class_sig = "class AnonymousScheme(BaseScheme):\n"
        class_body = f"    {self.name} = FieldIns\n"

        exec(class_sig + class_body, exec_namespace, exec_result)
        return exec_result["AnonymousScheme"]


T = typing.TypeVar('T')
def field(
    default: T | Undefined = _undefined, 
    default_factory: Opt[typing.Callable[[], T]] = None,
    name: Opt[str] = None,
    is_key: bool = False,
    is_natural_key: bool = True,
    is_foreign_key: bool = False,
    converter: Opt[BaseConverter] = None,
    validators: Opt[typing.Iterable['BaseValidator']] = None,
    is_partial: bool = False,
    dump_flags: Opt[set[str]] = None,
    init: bool = True
):
    return Field[T](
        default=default, 
        default_factory=default_factory, 
        name=name, 
        is_key=is_key,
        is_natural_key=is_natural_key,
        is_foreign_key=is_foreign_key, 
        converter=converter,
        validators=validators,
        is_partial=is_partial,
        dump_flags=dump_flags,
        init=init
    )


class PrivateField[FieldValueType](Field[FieldValueType]):

    """碧霄私有字段

    - 不会被外部访问？（setting 那边的实践有问题）
    - 不会被序列化
    - 不会与数据访问层交互（无需代理）
    - 不会被校验
    - 实例化时不是必须的
    """
    
    @property
    def name(self): raise ValueError('Private field name is forbidden')
    
    def __set__(self, instance: "BaseScheme", value: FieldValueType) -> None:
        instance._set_value(self, value)

def private_field(
    default: T | Undefined = _undefined,
    default_factory: Opt[typing.Callable[[], T]] = None,
):
    
    return PrivateField[T](
        default=default, 
        default_factory=default_factory, 
    )


SchemeTV = typing.TypeVar("SchemeTV", bound="BaseScheme")
class CompositeField(
    Field[SchemeTV],
    typing.Generic[SchemeTV], 
):
    """

    - Enable partial for composite field makes sub scheme partial.
    """
    
    @property
    def name(self): 
        raise ValueError("CompositeField don't has a name")
    def _set_name(self, value: str, no_raise: bool = False) -> None:
        if no_raise:
            return None
        raise ValueError("CompositeField can't have a name")
    
    def dump_val_to_jsonable(self, value: SchemeTV) -> typing.Dict[str, typing.Any]:
        return value.dump_to_dict(jsonable=True)
    
    @property
    def sub_fields(self) -> typing.Iterable[Field]:
        return self.vtype.__fields__.values()
    
    @property
    def _sub(self) -> typing.Type[SchemeTV]:
        return self.vtype


def get_default(field: Field[T]) -> T:

    '''Get field's default value.

    :raise ValueError: 
    '''
    return typing.cast(Field[T], field).default_value

def dump_field_name(field: Field | str, in_scheme: bool = False) -> str:

    if isinstance(field, Field):
        return field.name if not in_scheme else field.in_scheme_name
    return field


FieldTV = typing.TypeVar('FieldTV', bound=Field)
"""字段类型变量"""
