"""BF Model Field module"""

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
from ..utils.typing_ import safe_issubclass
from .converter import BaseConverter, get_converter_from_anno

if typing.TYPE_CHECKING:
    from .main import BaseModel
    from .validator import BaseValidator


FieldValueTV = typing.TypeVar('FieldValueTV')
class FieldValueProxy(typing.Generic[FieldValueTV]):
    """Field Value Proxy

    字段值必然是原生值，不能是用户自定义类

    - 检测对可变对象的修改
    - 获得所属的字段实例

    Implementation
    --------------
    透明代理
    ^^^^^^^^^^
    - 在下方通过 for 循环注册了一堆特殊方法
    - `__bool__` 特殊处理
    """

    def __init__(self, 
        obj: FieldValueTV, 
        modified: typing.Callable,
        field: "Field[FieldValueTV]",
        model: "BaseModel"
    ) -> None:

        self._obj: FieldValueTV = obj
        self._modified = modified
        self._field: "Field[FieldValueTV]" = field
        self._model: "BaseModel" = model

    @property
    def model(self): return self._model
    
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
        
        if name in ('_obj', '_modified', '_field', '_model'):
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
    __model__: "BaseModel"


class Field(typing.Generic[FieldValueTV]):

    """BF Model Field.

    Responsibilities
    ----------------
    - Describes field metadata (name, type, default value, etc.)
    - Defines field constraints through validators and converters
    - Provides field-level value access (descriptor protocol)
    - Stores field configuration (is_key, is_partial, etc.)
    
    Note: Serialization logic is handled by ModelConverter. Field masks 
    in ModelConverter control which fields are included in serialization.

    Features
    --------
    Validator
    ^^^^^^^^^
    See :doc:`/design/model/validator`

    Inherit
    ^^^^^^^
    - Make sure your `__init__` accepts the same parameters as `Field` or use
    `**kwargs` to achieve that. (Set your parameters in kwargs to avoid conflict)
      Or set your parameters in `_post_init` instead of
    overriding `__init__`.
    """

    def __init__(
        self, 
        default: typing.Union[Undefined, FieldValueTV] = _undefined, 
        default_factory: Opt[typing.Callable[[], FieldValueTV]] = None,
        vtype: Undefined | typing.Type[FieldValueTV] = _undefined,
        name: Opt[str] = None,
        in_model_name: Opt[str] = None,
        model_cls: Opt[typing.Type["BaseModel"]] = None,
        is_key: bool = False,
        is_key_natural: bool = False,
        is_foreign_key: bool = False,
        converter: Opt[BaseConverter[FieldValueTV]] = None,
        validators: Opt[typing.Iterable["BaseValidator"]] = None,
        is_partial: bool = False,
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
        :param in_model_name:
            Field name in model.
        :param model_cls:
            Model class this field attached on.
        :param converter:
            See :doc:`/design/model/converter`
        :param validators:
            See :doc:`/design/model/validator`
        :param is_partial:
            If True, field value left undefined if not provided, and
            default value will not be applied.
        :param is_key: 
            This field is a key
        :param is_key_natural:
            If this field is a key, it is managed by DataSource (False for surrogate)
        :param is_foreign_key:
            If you want to mark a primary or composite key, use KeyField instead
        :param init: 
            see `Dataclass field specifier parameters <https://typing.python.org/en/latest/spec/dataclasses.html#field-specifier-parameters>`_
        """
        self.__name = name
        self.__in_model_name = in_model_name or name
        self.__model_cls = model_cls
        self.__default = default
        self.__default_factory = default_factory
        self.__vtype = vtype
        self.__is_key = is_key
        self.__is_key_natural = is_key_natural
        self.__is_foreign_key = is_foreign_key
        self.__converter: BaseConverter | None = converter
        self.__validators: typing.List["BaseValidator"] = list(validators or [])
        self.__is_partial = is_partial
        self.__init = init

    # FIXME all default must be negative, or default value will override original value even if \
    #  no new value is set
    def fork(
        self,
        default: Undefined | FieldValueTV = _undefined,
        default_factory: Opt[typing.Callable[[], FieldValueTV]] = None,
        vtype: Undefined | typing.Type[FieldValueTV] = _undefined,
        name: Opt[str] = None,
        in_model_name: Opt[str] = None,
        model_cls: Opt[typing.Type["BaseModel"]] = None,
        is_key: bool = False,
        is_key_natural: bool = False,
        is_foreign_key: bool = False,
        converter: Opt[BaseConverter[FieldValueTV]] = None,
        fork_validators: bool = False,
        is_partial: Opt[bool] = None,
        init: Opt[bool] = None,
    ) -> typing.Self:
        return self.__class__(
            default=default if default is not _undefined else self.__default,
            default_factory=default_factory or self.__default_factory,
            name=name or self.__name,
            in_model_name=in_model_name or self.__in_model_name,
            model_cls=model_cls or self.__model_cls,
            is_key=is_key or self.__is_key,
            is_key_natural=is_key_natural or self.__is_key_natural,
            is_foreign_key=is_foreign_key or self.__is_foreign_key,
            converter=converter or self.__converter,
            validators=self.__validators if fork_validators else None,
            is_partial=is_partial or self.__is_partial,
            init=init or self.__init,
            vtype=vtype if vtype is not _undefined else self.__vtype
        )
    
    def __hash__(self) -> int:
        """哈希值

        in_model_name or name
        """
        return hash(self.__in_model_name or self.__name)
    
    def __eq__(self, value) -> bool:

        """Make Field(name='name') == 'name'
        """
        if isinstance(value, str):
            return self.__name == value or self.__in_model_name == value
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
    def in_model_name(self) -> str:
        if self.__in_model_name is None:
            raise ValueError('Field in_model_name is not defined')
        return self.__in_model_name
    
    def is_key(self) -> bool: 
        return self.__is_key
    def is_key_natural(self) -> bool:
        return self.__is_key_natural

    def _set_name(self, value: str, no_raise: bool = False) -> None:
        """设置字段名称

        如果已经设置过名称，则抛出错误；如果不想抛出错误，则传入 ``no_raise`` 参数为 ``True``
        """
        if self.__name is not None:
            if no_raise:
                return None
            raise ValueError('Field name is immutable')
        self.__name = value

    def _set_in_model_name(self, value: str, no_raise: bool = False) -> None:
        """设置字段在数据模型中的名称

        如果已经设置过名称，则抛出错误
        """
        if self.__in_model_name is not None:
            if no_raise:
                return None
            raise ValueError('Field in_model_name is immutable')
        self.__in_model_name = value

    @property
    def vtype(self) -> typing.Type[FieldValueTV]:
        if self.__vtype is _undefined:
            raise ValueError(f"vtype is not set on field {self.name}")
        return self.__vtype
    
    @property
    def is_partial(self) -> bool:
        return self.__is_partial

    @property
    def model_cls(self) -> typing.Type["BaseModel"]: 
        if self.__model_cls is None:
            raise ValueError('Field model is not defined')
        return self.__model_cls
    
    def _set_model_cls(self, 
        model_cls: Opt[typing.Type["BaseModel"]],
        no_raise: bool = False,
        force: bool = False
    ) -> None:
        """设置字段所属的数据模型

        如果已经设置过数据模型，则抛出错误

        :param force: 是否强制设置 \n
            建议使用 :meth:`fork` 来设置值（但元类是特例）
        """
        if self.__model_cls is not None and not force:
            if no_raise: return None
            raise ValueError('Field model is immutable')
        self.__model_cls = model_cls

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

        - 支持 `Field[type]`
        - 支持 `FieldSubclass` （必须是直接子类，不能是孙类）
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

    def load_val(self, value: typing.Any) -> FieldValueTV:
        if value is _undefined:
            return self.default_value
        else:
            return self.convert(value)
    
    @property
    def converter(self) -> BaseConverter:
        if self.__converter is None:
            raise ValueError('converter is not defined on field %s' % self.in_model_name)
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
            raise ValueError('No default value provided for field %s' % self.in_model_name)
    
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
        model_ins: Opt["BaseModel"] = None,
    ) -> None:
        """Run validator bind to this field.

        :raises ValueError: If invalid.
        """
        for validator in self.__validators:
            validator(value, model_ins=model_ins)

    @typing.overload
    def __get__(self, instance: None, owner) -> typing.Self:
        ...

    @typing.overload
    def __get__(self, instance: "BaseModel", owner) -> FieldValueTV:
        # 实际上是 FieldValueProxy[FieldValueType]
        ...
    
    def __get__(self, instance: Opt["BaseModel"], owner) \
        -> "Field" | FieldValueTV:

        if instance is None:
            return self
        return typing.cast(FieldValueTV, instance._get_value(self))
        
    def __set__(self, instance: "BaseModel", value: FieldValueTV) -> None:
        """
        .. versionchanged:: 0.1.2
            if initialized, set to undefined will change nothing
        """
        initialized = self.in_model_name in instance.__field_values__

        # convert value
        if value is _undefined:
            if initialized:
                return  # remain value unchanged

            instance._mark_unset(self.in_model_name)
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
        self.validate(value, model_ins=instance)

        if instance.__proxy__:
            value_ = self._proxy_value(value, instance)
        else:
            value_ = value
        
        instance._set_value(self, value_)  # save

        # if already initialized, mark as dirty
        if initialized:
            instance._mark_dirty(self.in_model_name)

    def _proxy_value(self, 
        value: FieldValueTV, instance: "BaseModel"
    ) -> FieldValueProxy[FieldValueTV]:
        
        if not isinstance(value, FieldValueProxy):
            # 避免循环代理
            return FieldValueProxy(
                value, 
                lambda: instance._mark_dirty(self.in_model_name),
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

    def dump_to_model(self) -> typing.Type["BaseModel"]:

        """
        根据字段实例创建数据模型

        这个数据模型只包含本字段
        """
        from .main import BaseModel

        exec_namespace = {
            "BaseModel": BaseModel,
            "FieldIns": self,
        }
        exec_result = {}

        class_sig = "class AnonymousModel(BaseModel):\n"
        class_body = f"    {self.name} = FieldIns\n"

        exec(class_sig + class_body, exec_namespace, exec_result)
        return exec_result["AnonymousModel"]


T = typing.TypeVar('T')
def field(
    default: T | Undefined = _undefined, 
    default_factory: Opt[typing.Callable[[], T]] = None,
    name: Opt[str] = None,
    is_key: bool = False,
    is_natural_key: bool = False,
    is_foreign_key: bool = False,  # TODO no needed, remove
    converter: Opt[BaseConverter] = None,
    validators: Opt[typing.Iterable['BaseValidator']] = None,
    is_partial: bool = False,
    init: bool = True
):
    return Field[T](
        default=default, 
        default_factory=default_factory, 
        name=name, 
        is_key=is_key or is_natural_key,
        is_key_natural=is_natural_key,
        is_foreign_key=is_foreign_key, 
        converter=converter,
        validators=validators,
        is_partial=is_partial,
        init=init
    )


class PrivateField[FieldValueType](Field[FieldValueType]):

    """BF Private Field

    - 不会被外部访问？（setting 那边的实践有问题）
    - 不会被序列化
    - 不会与数据访问层交互（无需代理）
    - 不会被校验
    - 实例化时不是必须的
    """
    
    @property
    def name(self): raise ValueError('Private field name is forbidden')
    
    def __set__(self, instance: "BaseModel", value: FieldValueType) -> None:
        try:
            if value is _undefined:
                value = self.default_value
        except ValueError:
            value = _undefined
        instance._set_value(self, value)

def private_field(
    default: T | Undefined = _undefined,
    default_factory: Opt[typing.Callable[[], T]] = None,
):
    
    return PrivateField[T](
        default=default, 
        default_factory=default_factory, 
    )


ModelTV = typing.TypeVar("ModelTV", bound="BaseModel")
class CompositeField(
    Field[ModelTV],
    typing.Generic[ModelTV], 
):
    """Composite Field

    - Enable partial for composite field makes sub model partial.
    """
    
    @property
    def name(self): 
        raise ValueError("CompositeField don't has a name")
    def _set_name(self, value: str, no_raise: bool = False) -> None:
        if no_raise:
            return None
        raise ValueError("CompositeField can't have a name")
    
    @property
    def sub_fields(self) -> typing.Iterable[Field]:
        return self.vtype.__fields__.values()
    
    @property
    def _sub(self) -> typing.Type[ModelTV]:
        return self.vtype


def get_default(field: Field[T]) -> T:

    '''Get field's default value.

    :raise ValueError: 
    '''
    return typing.cast(Field[T], field).default_value

def dump_field_name(field: Field | str, in_model: bool = False) -> str:

    if isinstance(field, Field):
        return field.name if not in_model else field.in_model_name
    return field


FieldTV = typing.TypeVar('FieldTV', bound=Field)
"""字段类型变量"""
