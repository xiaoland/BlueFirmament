
__all__ = [
    'SchemeMetaclass',
    'BaseScheme', 
    'SchemeTV',
    'NoProxyScheme',
    'BaseRootScheme',
    "merge"
]

import abc
import copy
import inspect
from re import I
import types
import typing
from typing import Optional as Opt, Annotated as Anno, Literal as Lit
from ..utils.type import safe_issubclass
from .._types import Undefined, _undefined
from .validator import SchemeValidator, FieldValidator
from .field import (
    CompositeField, PrivateField, Field, 
    field, dump_field_name
)
from .field import FieldValueProxy
if typing.TYPE_CHECKING:
    from ..dal.types import DALPath
    from ..log import LoggerT
    from ..dal.filters import DALFilter, EqFilter
    from ..dal.base import DataAccessLayer


@typing.dataclass_transform(
    kw_only_default=True,
    field_specifiers=(
        Field, CompositeField,
        field
    )
)
class SchemeMetaclass(abc.ABCMeta):

    """碧霄数据模型元类

    Design Doc: :doc:`/design/scheme/index`

    Rational
    ---------
    - 允许数据模型通过类属性定义字段

    Attributes
    -----------
    - ``__table_name__``：表名
    - ``__schema_name__``：数据库名
    - ``__fields__``：字段字典

    Usage
    -------
    定义字段
    ^^^^^^^^^

    基本示例：

    ```python
    class MyScheme(BlueFirmamentScheme):
        table_name = 'my_table'
        
        _id: BlueFirmamentSequenceField = BlueFirmamentField(is_primary_key=True)  # 类型为自增的字段
        name: str = 'default_name'
    ```
    
    可以直接使用`BlueFirmamentField`定义字段，也可以直接使用值定义字段。值将会作为字段的默认值，类变量名将自动作为字段名。

    名称为下列的类变量会被解析为内置字段：（不会继承）
    - ``_table_name``：表名
    - ``_schema_name``：数据库名/表组名（来源于PostgreSQL，相当于MySQL的数据库）

    声明私有字段使用``BlueFirmamentPrivateField``

    数据模型实例化
    ^^^^^^^^^^^^^^^^
    - 未传递的字段将使用默认值，没有默认值将变为BlueFirmamentUndefinedValue

    Behavior
    ---------
    字段继承
    ^^^^^^^^^^
    - 普通字段和私有字段都会被继承
    - 按照MRO顺序继承（往后的优先级更高）
    - 如果声明了同名字段且不是一个字段实例，会复制并覆盖（默认值、名称）

    """

    __builtin_cvars__: typing.Dict[str, typing.Any] = {
        '__dal__': None,
        '__dal_path__': None, 
        '__proxy__': False,
        '__disable_log__': False,
        '__key__': None,
        '__fields__': dict,
        '__partial__': False,
        '__inherit_validators__': True,
        '__private_fields__': dict,
        '__scheme_validators__': list,
        '__after_field_validators__': list,
        '__default_edflags__': None,
        '__default_idflags__': None
    }
    """Builtin class variables of BlueFirmamentScheme
    
    values are the default value (callable for mutable values).
    """
    __builtin_ivars__: typing.Dict[str, typing.Any] = {
        '__logger__': None,
        '__instantiated__': False,
        '__unset_fields__': set,
        '__dirty_fields__': set,
        '__field_values__': dict,
    }
    """Builtin instance variables of BlueFirmamentScheme
    
    values are the default value (callable for mutable values).
    """

    def __new__(
        cls, name: str, 
        bases: typing.Tuple[type[typing.Any], ...], 
        attrs: typing.Dict[str, typing.Any],
        dal_path: Opt["DALPath"] = None,
        dal: Opt[typing.Type["DataAccessLayer"]] = None,
        proxy: Opt[bool] = None,
        disable_log: Opt[bool] = None,
        partial: Opt[bool] = None,
        inherit_validators: Opt[bool] = None,
        default_exclude_dump_flags: Opt[set[str]] = None,
        default_include_dump_flags: Opt[set[str]] = None,
        **kwargs
    ):

        # Exclude base scheme class
        if name in ("BaseScheme",):
            return super().__new__(cls, name, bases, attrs, **kwargs)

        # Set up class vars
        if dal_path:
            attrs["__dal_path__"] = dal_path
        if dal:
            attrs["__dal__"] = dal
        if proxy:
            attrs["__proxy__"] = proxy
        if disable_log:
            attrs["__disable_log__"] = disable_log
        if partial:
            attrs["__partial__"] = partial
        if inherit_validators:
            attrs["__inherit_validators__"] = inherit_validators
        if default_exclude_dump_flags:
            attrs["__default_edflags__"] = default_exclude_dump_flags
        if default_include_dump_flags:
            attrs["__default_idflags__"] = default_include_dump_flags
        for builtin_f, default_v in cls.__builtin_cvars__.items():
            if builtin_f not in attrs:
                # Find in bases
                for base in bases:
                    if hasattr(base, builtin_f):
                        attrs[builtin_f] = copy.copy(getattr(base, builtin_f))
                        break
                else:
                    attrs[builtin_f] = default_v if not callable(default_v) else default_v()
        
        # Resolve fields
        fields: typing.Dict[str, Field] = attrs['__fields__']
        fields.update({
            k: v.fork(fork_validators=attrs['__inherit_validators__'])
            for k, v in fields.items()
        })
        private_fields: typing.Dict[str, PrivateField] = attrs['__private_fields__']
        private_fields.update({
            k: v.fork(fork_validators=attrs['__inherit_validators__'])
            for k, v in private_fields.items()
        })
        scheme_validators: typing.List[SchemeValidator]
        if not attrs['__inherit_validators__']:
            scheme_validators = list()
            attrs['__scheme_validators__'] = scheme_validators
        else:
            scheme_validators = attrs['__scheme_validators__']

        # Resolve attrs
        for k, v in attrs.items():

            # Skip dunder methods
            if k.startswith('__') and k.endswith('__'):
                continue

            # Skip method and function
            if inspect.ismethoddescriptor(v):
                continue
            elif inspect.isfunction(v):
                continue

            # Skip property
            if isinstance(v, property):
                continue

            # Resolve scheme validators
            if isinstance(v, SchemeValidator):
                scheme_validators.append(v)
                continue


            # Resolve private fields 
            if isinstance(v, PrivateField):
                private_fields[k] = v
                v._set_name(k, True) # 如果没有配置名称，则使用类变量名作为字段名
                v._set_in_scheme_name(k, True)
                continue

            # Resolve fields
            if isinstance(v, Field):
                # already a field instance
                fields[k] = v
                v._set_name(k, True) # try to set name
                v._set_in_scheme_name(k, True)
            else:
                # not a field instance
                if k in fields:
                    fields[k] = fields[k].fork(
                        default=v, name=k, in_scheme_name=k
                    )
                    continue
                elif k in private_fields:
                    private_fields[k] = private_fields[k].fork(
                        default=v, name=k, in_scheme_name=k,
                    )
                    continue

                fields[k] = Field(v, name=k, in_scheme_name=k)

        # Set up field converter from annotations
        for k, field_ in (fields | private_fields).items():
            anno = attrs.get('__annotations__', {}).get(k)
            if anno:
                field_._set_converter_from_anno(anno)

        # Resolve attrs having only annotation
        cls_annotations = attrs.get('__annotations__', {})
        for k, anno in cls_annotations.items():

            if k.startswith('__') and k.endswith('__'):
                continue
            
            if k not in fields and k not in private_fields:
                # Field[ValueT]
                orig = typing.get_origin(anno)
                if safe_issubclass(orig, Field):
                    field = orig(
                        name=k, in_scheme_name=k, 
                        vtype=typing.get_args(anno)[0]
                    )
                    field._set_converter_from_anno(anno)
                    fields[k] = field
                    continue

                # ValueT
                # not yet resolved above
                fields[k] = Field(name=k, in_scheme_name=k, vtype=anno)
                fields[k]._set_converter_from_anno(anno)


        # Replace attributes that recognized as fields' value to field instance
        for k, default_v in (fields | private_fields).items():
            attrs[k] = default_v

        # Resolve key field
        for v in fields.values():
            if v.is_key(): 
                attrs['__key__'] = v
                break


        # dynamically create __init__ method
        init_params: set[str] = set()
        init_assignments = []
        new_globals = globals().copy()
        for k, field_ins in (fields | private_fields).items():
            # skip init=False
            if not field_ins.init:
                continue
            
            # type_str = cls._get_type_from_anno(cls_annotations, k, new_globals)
            init_params.add(k)
            if isinstance(field_ins, CompositeField):
                sub_scheme_name = field_ins._sub.__name__
                if field_ins.is_partial or attrs['__partial__']:
                    partial_sub_scheme = copy.copy(field_ins._sub)
                    setattr(partial_sub_scheme, '__partial__', True)
                    new_globals[sub_scheme_name] = partial_sub_scheme
                else:
                    new_globals[sub_scheme_name] = field_ins._sub

                for sub_field in field_ins.sub_fields:
                    init_params.add(sub_field.in_scheme_name)

                init_assignments.append(f"    self.{k} = {k} if {k} is not _undefined \
                    else {sub_scheme_name}({
                    ",".join(
                        f"{i.in_scheme_name}={i.in_scheme_name}"
                        for i in field_ins.sub_fields
                    )
                })")
            else:
                init_assignments.append(f"    self.{k} = {k}")
        
        if init_params:
            init_sig = f"def __init__(self, *, {','.join(f'{i}=_undefined' for i in init_params)}, **kwargs):\n"
        else:
            init_sig = "def __init__(self, **kwargs):\n"
        init_body = '\n'
        init_body += '    SchemeMetaclass.init_ivars(self)\n'
        init_body += '\n'.join(init_assignments)
        init_body += '\n    SchemeMetaclass.run_scheme_validators(self)\n'
        init_body += '    self.__post_init__()\n'
        init_body += '    self.__instantiated__ = True\n'
        init_body += '    SchemeMetaclass.run_after_field_validators(self)\n'
        init_body += '    if not self.__disable_log__:\n'
        init_body += '        self._logger.info("Scheme instantiated", scheme_data=self.dump_to_dict())\n'

        init_method = init_sig + init_body
        
        exec(init_method, new_globals, attrs)

        result_class = super().__new__(cls, name, bases, attrs, **kwargs)

        # set fields' scheme
        for k, default_v in (result_class.__fields__).items():
            default_v._set_scheme_cls(
                typing.cast(typing.Type["BaseScheme"], result_class), 
                no_raise=True, force=True
            )

        return result_class
    
    @staticmethod
    def _get_type_from_anno(cls_annotations, k: str, globols):
        type_: typing.Type | types.UnionType | None = cls_annotations.get(k, None)
        if type_ is None:
            type_str = 'typing.Any'
        elif isinstance(type_, types.UnionType):
            type_str = '|'.join([t.__name__ for t in type_.__args__])
            type_str = type_str.replace('NoneType', 'None')
        else:
            type_str = type_.__name__
            globols[type_str] = type_

        return type_str
    
    @staticmethod
    def init_ivars(ins: "BaseScheme"):
        """Initialize instance variables
        """
        for k, default_v in SchemeMetaclass.__builtin_ivars__.items():
            setattr(ins, k, default_v() if callable(default_v) else default_v)

    @staticmethod
    def run_scheme_validators(ins: "BaseScheme"):
        for validator in ins.__scheme_validators__:
            validator(ins)

    @staticmethod
    def run_after_field_validators(ins: "BaseScheme"):
        for _ in range(len(ins.__after_field_validators__)):
            validator = ins.__after_field_validators__.pop(0)
            validator(value=ins[validator._field], scheme_ins=ins)


TV = typing.TypeVar("TV")


class BaseScheme(metaclass=SchemeMetaclass):
    """Base data model class of BlueFirmament

    Features
    ---------
    Serialization
    ^^^^^^^^^^^^^

    Partial
    ^^^^^^^
    Partial field will remain undefined if not provided during instantiation and
    no default value set, otherwise raise `ValueError`.

    Set `__partial__` to `True` to make all fields partial, you can override this
    in each field definition.
    """

    # class vars
    __dal__: Opt[typing.Type["DataAccessLayer"]]
    __dal_path__: Opt["DALPath"]
    __key__: Opt[Field]  # TODO use field
    """Field that uniquely identifies an instance.

    Includes primary key, composite key.
    """
    __disable_log__: bool
    """Disable scheme internal logs
    """
    __proxy__: bool
    """Proxy field value or not

    If disabled:
    - Mutable field value modification will not be tracked
    - Cannot get scheme or field info from field value
    """
    __fields__: typing.Dict[str, Field]
    """Fields and their instances defined in the scheme
    """
    __private_fields__: typing.Dict[str, PrivateField]
    """Private fields and their instances defined in the scheme
    """
    __scheme_validators__: typing.List[SchemeValidator]
    __after_field_validators__: typing.List[FieldValidator]
    """Field validators needed to be ran
    immediately after scheme instantiation
    """
    __partial__: bool
    """If True, all fields are partial
    """
    __inherit_validators__: bool
    """If False, scheme and field validators will not be inherited by
    sub scheme.
    """
    __default_edflags__: Opt[set[str]]
    __default_idflags__: Opt[set[str]]

    # instance vars
    __field_values__: typing.Dict[str, typing.Any]
    """Storing each field's value
    
    - Key is the field's in_scheme_name.
    """
    __dirty_fields__: typing.Set[str]
    """Which fields are modified since last dump

    - Exclude private fields.
    """
    __unset_fields__: typing.Set[str]
    """Fields that are not provided during instantiation

    - Exclude private fields
    - Instance variable
    """
    __logger__: Opt["LoggerT"]
    """Scheme level logger

    - Instance variable
    """
    __instantiated__: bool
    """Whether the scheme is instantiated

    - Instance variable
    """

    def __post_init__(self) -> None:
        """数据模型实例化后执行的操作；可以被重写"""

    @staticmethod
    def _init_private_fields(obj: 'BaseScheme', data: typing.Any):

        for k, v in obj.__private_fields__.items():
            if k in data:
                setattr(obj, k, v.convert(data[k]))
            else:
                setattr(obj, k, v.default_value)

    @classmethod
    def from_parents(cls, /, *parents: "BaseScheme") -> typing.Self:

        """从父数据模型实例实例化本数据模型
        """
        data = {}
        for parent in parents:
            data.update(parent.__field_values__)

        return cls(**data)

    def _mark_unset(
        self, field_: str | Field
    ) -> None:
        """Mark field as unset (not provided during instantiation)
        """
        if isinstance(field_, Field):
            self.__unset_fields__.add(field_.in_scheme_name)
        else:
            self.__unset_fields__.add(field_)

    def _mark_dirty(self, field_: str | Field) -> None:
        """Mark field as dirty (modified since last dump)
        """
        if isinstance(field_, str):
            field_ = self.__fields__[field_]
        self.__dirty_fields__.add(field_.name)

    @classmethod
    def dal_path(cls) -> "DALPath":
        """
        :raise ValueError: when not set
        """
        if not cls.__dal_path__:
            raise ValueError("dal path not set")
        return cls.__dal_path__
    
    def equals(self) -> typing.Tuple["DALFilter", ...]:
        """Get EqFilter of all fields.
        """
        return tuple(
            field.equals(self._get_value(field))
            for field in self.__fields__.values()
        )

    @classmethod
    def get_key_field(cls) -> Field:
        """
        :raise KeyError: if no key on scheme
        """
        if not cls.__key__:
            raise KeyError(f'{cls.__name__} does not have a key')
        return cls.__key__
    
    @property
    def key_value(self) -> typing.Any:
        return self._get_value(self.get_key_field())
    
    @property
    def key_eqf(self) -> "EqFilter":
        key_field = self.get_key_field()
        return key_field.equals(self._get_value(key_field))
    
    # def dump(self, target_type: typing.Type[TV]) -> TV:
    #     """Serialize
    #     """
    #     if target_type is str:
    #         return self.dump_to_str()
    #     elif target_type is dict:
    #         return self.dump_to_dict()

    def __str__(self):
        return self.dump_to_str()

    def dump_to_str(
        self,
        use_name: bool = False
    ) -> str:
        """Serialize model to string

        :param use_name: use field's name instead of in_scheme_name,
                        defaults to False
        :type use_name: bool, optional
        """
        return ",".join(
            f"{in_name if not use_name else i.name}={\
                i.dump_val_to_str(FieldValueProxy.dump(self[i]))}"
            for in_name, i in self.__fields__.items()
        )

    def dump_to_dict(
        self,
        only_dirty: bool = False,
        exclude_natural_key: bool = False,
        exclude_unset: Opt[bool] = None,
        exclude_flags: Opt[set[str]] = None,
        include_flags: Opt[set[str]] = None,
        jsonable: bool = True
    ) -> dict:

        """Serialize to (jsonable) dict

        :param only_dirty: 
            If True, dirty fields will be reset.
        :param exclude_natural_key:
            If True, exclude natural key field.
        :param exclude_unset:
            If True, exclude unset fields.
            If None and is partial scheme, defaults to True.
        :param exclude_flags:
            If provided, exclude fields with all these flags.
            If not provided, ``default_exclude_dump_flags`` configured on
            scheme will be used.
            Prior to ``include_flags`` (same for scheme default).
        :param include_flags:
            If provided, only dumps fields with all these flags.
            If not provided, ``default_include_dump_flags`` configured on
            scheme will be used.
        :param jsonable:
            If True, ensure the return is jsonable.

        Behaviour
        ----------
        - 调用每个字段的校验器来序列化字段值
        """
        data = dict()
        field_names: typing.Set[str] = set()

        if only_dirty:
            field_names = self.__dirty_fields__
        else:
            field_names = set(self.__fields__.keys())

        if exclude_natural_key:
            key_field = self.get_key_field()
            if key_field.is_natural_key():
                field_names = field_names - {key_field.in_scheme_name}

        if exclude_unset is True or (exclude_unset is None and self.__partial__):
            field_names = field_names - self.__unset_fields__

        if exclude_flags is None and self.__default_edflags__:
            exclude_flags = self.__default_edflags__

        if include_flags is None and self.__default_idflags__:
            include_flags = self.__default_idflags__

        for k in field_names:
            field: Field = self.__fields__[k]

            if exclude_flags:
                if field.dump_flags.issuperset(exclude_flags):
                    continue

            if include_flags and not exclude_flags:
                if not field.dump_flags.issuperset(include_flags):
                    continue
                
            field_v = FieldValueProxy.dump(getattr(self, k))
            if jsonable:
                if isinstance(field, CompositeField):
                    data.update(field.dump_val_to_jsonable(field_v))
                else:
                    data[k] = field.dump_val_to_jsonable(field_v)
            else:
                data[k] = field_v
        
        return data
    
    def __getitem__(self, key: str | Field) -> typing.Any:
        
        """通过字段名/字段获取字段值

        Note: 不可以是其他属性，只可以是字段
        """
        if key in self.__fields__:
            return getattr(self, dump_field_name(key, in_scheme=True))
        
        raise KeyError(f'{key} is not a field of {self.__class__.__name__}')
    
    def __setitem__(self, key: str | Field, value: typing.Any) -> None:

        """通过字段/字段名设置字段值

        Note: 不可以是其他属性，只可以是字段
        """
        field = self.__getitem__(key)
        field.__set__(self, value)

    @classmethod
    def keys(cls) -> typing.Iterable[str]:
        
        """获取所有字段的名称的集合
        """
        return cls.__fields__.keys()
    
    def values(self) -> typing.Iterable[typing.Any]:

        """获取所有字段的值的集合
        """
        return self.__field_values__.values()
    
    FieldValueType = typing.TypeVar("FieldValueType")

    def _set_value(
        self, field: Field[FieldValueType], 
        value: "FieldValueProxy[FieldValueType]" | FieldValueType | Undefined
    ) -> None:

        """设置字段值

        :param field: 字段名或字段实例
        """
        self.__field_values__[field.in_scheme_name] = value

    def _get_value(
        self, field: Field[FieldValueType]
    ) -> "FieldValueProxy[FieldValueType]" | FieldValueType:

        """获取字段值

        :param field: 字段名或字段实例
        """
        return self.__field_values__[field.in_scheme_name]
    
    @property
    def _logger(self):
        """Scheme level logger

        Context:
        - scheme_id: id(self)
        """
        if not self.__logger__:
            from ..log import get_logger
            logger = get_logger(self.__class__.__name__)
            logger = logger.bind(
                scheme_id=id(self),
            )
            self.__logger__ = logger
        return self.__logger__
    
    def _set_logger(self, logger: "LoggerT") -> None:
        """Set scheme level logger"""
        self.__logger__ = logger


SchemeTV = typing.TypeVar('SchemeTV', bound=BaseScheme)
"""数据模型类型变量
"""


class NoProxyScheme(BaseScheme,
    proxy=False                    
):
    pass


class BaseRootScheme(BaseScheme):

    """根数据模型类

    - 只有一个 root 字段
    - 序列化时 root 不会作为字段名，而是直接序列化 root 字段的值
    """

    root: Field


def merge(scheme1: BaseScheme, scheme2: BaseScheme) -> None:
    """Merge same fields (by name)'s value from scheme2 to scheme1.

    Examples
    --------
    >>> merge(SchemeA(a=1, b=3), SchemeB(a=2))
    SchemeA: a=2, b=3
    >>> merge(SchemeA(a=1), SchemeB(a=_undefined))
    SchemeB: a=1
    """
    for field_ in scheme2.__fields__.values():
        try:
            scheme1[field_] = scheme2[field_]
        except KeyError:
            continue

