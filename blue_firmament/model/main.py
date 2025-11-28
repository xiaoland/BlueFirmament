
__all__ = [
    # New names (BF prefix)
    'BFModelMetaclass',
    'BFModel',
    'BaseModel',
    'ModelTV',
    'NoProxyModel',
    'BaseRootModel',
    'merge',
]

import abc
import copy
import inspect
import types
import typing
from typing import Optional as Opt

from ..utils.typing_ import safe_issubclass
from .._types import Undefined, _undefined
from .validator import ModelValidator, FieldValidator
from .field import (
    CompositeField, PrivateField, Field, 
    field, dump_field_name
)
from .field import FieldValueProxy
if typing.TYPE_CHECKING:
    from ..log import LoggerT


@typing.dataclass_transform(
    kw_only_default=True,
    field_specifiers=(
        Field, CompositeField,
        field
    )
)
class BFModelMetaclass(abc.ABCMeta):

    """BF Model Metaclass (碧霄数据模型元类)

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
    class MyModel(BFModel):
        table_name = 'my_table'
        
        _id: BFSequenceField = BFField(is_primary_key=True)  # 类型为自增的字段
        name: str = 'default_name'
    ```
    
    可以直接使用`Field`定义字段，也可以直接使用值定义字段。值将会作为字段的默认值，类变量名将自动作为字段名。

    名称为下列的类变量会被解析为内置字段：（不会继承）
    - ``_table_name``：表名
    - ``_schema_name``：数据库名/表组名（来源于PostgreSQL，相当于MySQL的数据库）

    声明私有字段使用``PrivateField``

    数据模型实例化
    ^^^^^^^^^^^^^^^^
    - 未传递的字段将使用默认值，没有默认值将变为Undefined

    Behavior
    ---------
    字段继承
    ^^^^^^^^^^
    - 普通字段和私有字段都会被继承
    - 按照MRO顺序继承（往后的优先级更高）
    - 如果声明了同名字段且不是一个字段实例，会复制并覆盖（默认值、名称）

    """

    __builtin_cvars__: typing.Dict[str, typing.Any] = {
        '__proxy__': False,
        '__key__': None,
        '__fields__': dict,
        '__partial__': False,
        '__inherit_validators__': True,
        '__private_fields__': dict,
        '__model_validators__': list,
        '__after_field_validators__': list,
        '__default_edflags__': None,
        '__default_idflags__': None
    }
    """Builtin class variables of BFModel
    
    values are the default value (callable for mutable values).
    """
    __builtin_ivars__: typing.Dict[str, typing.Any] = {
        '__instantiated__': False,
        '__unset_fields__': set,
        '__dirty_fields__': set,
        '__field_values__': dict,
    }
    """Builtin instance variables of BFModel
    
    values are the default value (callable for mutable values).
    """

    def __new__(
        cls, name: str, 
        bases: typing.Tuple[type[typing.Any], ...], 
        attrs: typing.Dict[str, typing.Any],
        proxy: Opt[bool] = None,
        partial: Opt[bool] = None,
        inherit_validators: Opt[bool] = None,
        default_exclude_dump_flags: Opt[set[str]] = None,
        default_include_dump_flags: Opt[set[str]] = None,
        **kwargs
    ):

        # Exclude base model classes
        if name in ("BaseScheme", "BaseModel", "BFModel"):
            return super().__new__(cls, name, bases, attrs, **kwargs)

        # Set up class vars
        if proxy:
            attrs["__proxy__"] = proxy
        if partial:
            attrs["__partial__"] = partial
        if inherit_validators:
            attrs["__inherit_validators__"] = inherit_validators
        if default_exclude_dump_flags:
            attrs["__default_edflags__"] = default_exclude_dump_flags
        if default_include_dump_flags:
            attrs["__default_idflags__"] = default_include_dump_flags
        for cvar, default_v in cls.__builtin_cvars__.items():
            if cvar not in attrs:
                # Find in bases
                found = False
                for base in reversed(bases):
                    if hasattr(base, cvar):
                        # FIXME multiple scheme to inherit from
                        if callable(default_v):
                            # mutable value
                            val = attrs.setdefault(cvar, default_v())
                            if isinstance(val, dict):
                                val.update(getattr(base, cvar))
                            elif isinstance(val, list):
                                val.extend(getattr(base, cvar))
                            else:
                                raise TypeError(
                                    f"Unsupported type {type(val)} for class variable {cvar}"
                                )
                        else:
                            # immutable value
                            attrs[cvar] = getattr(base, cvar)
                        
                        found = True
                        continue
                if not found:
                    attrs[cvar] = default_v if not callable(default_v) else default_v()
        
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
        model_validators: typing.List[ModelValidator]
        if not attrs['__inherit_validators__']:
            model_validators = list()
            attrs['__model_validators__'] = model_validators
        else:
            model_validators = attrs['__model_validators__']

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

            # Skip field validator(s)
            if isinstance(v, FieldValidator) or (
                isinstance(v, list) and isinstance(v[0], FieldValidator)
            ):
                continue

            # Resolve model validators
            if isinstance(v, ModelValidator):
                model_validators.append(v)
                continue

            # Resolve private fields 
            if isinstance(v, PrivateField):
                private_fields[k] = v
                v._set_name(k, True) # 如果没有配置名称，则使用类变量名作为字段名
                v._set_in_model_name(k, True)
                continue

            # Resolve fields
            if isinstance(v, Field):
                # already a field instance
                fields[k] = v
                v._set_name(k, True) # TODO rename as try
                v._set_in_model_name(k, True)
            else:
                # not a field instance
                if k in fields:
                    fields[k] = fields[k].fork(
                        default=v, name=k, in_model_name=k
                    )
                    continue
                elif k in private_fields:
                    private_fields[k] = private_fields[k].fork(
                        default=v, name=k, in_model_name=k,
                    )
                    continue

                fields[k] = Field(v, name=k, in_model_name=k)

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
                        name=k, in_model_name=k, 
                        vtype=typing.get_args(anno)[0]
                    )
                    field._set_converter_from_anno(anno)
                    fields[k] = field
                    continue

                # ValueT
                # not yet resolved above
                fields[k] = Field(name=k, in_model_name=k, vtype=anno)
                fields[k]._set_converter_from_anno(anno)


        # Replace attributes that recognized as fields' value to field instance
        for k, default_v in (fields | private_fields).items():
            attrs[k] = default_v

        # Resolve key field
        for v in fields.values():
            if v.is_key(): 
                attrs['__key__'] = v
                break


        # dynamically create __init__ method if not defined in attrs
        # If __init__ is defined in attrs, preserve it (it should call super().__init__())
        custom_init = attrs.get("__init__")
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
                sub_model_name = field_ins._sub.__name__
                if field_ins.is_partial or attrs['__partial__']:
                    partial_sub_model = copy.copy(field_ins._sub)
                    setattr(partial_sub_model, '__partial__', True)
                    new_globals[sub_model_name] = partial_sub_model
                else:
                    new_globals[sub_model_name] = field_ins._sub

                for sub_field in field_ins.sub_fields:
                    init_params.add(sub_field.in_model_name)

                init_assignments.append(f"    self.{k} = {k} if {k} is not _undefined \
                    else {sub_model_name}({
                    ",".join(
                        f"{i.in_model_name}={i.in_model_name}"
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
        init_body += '    BFModelMetaclass.init_ivars(self)\n'
        init_body += '\n'.join(init_assignments)
        init_body += '\n    BFModelMetaclass.run_model_validators(self)\n'
        init_body += '    self.__instantiated__ = True\n'
        init_body += '    BFModelMetaclass.run_after_field_validators(self)\n'
        init_body += '    self.__post_init__()\n'

        init_method = init_sig + init_body
        
        exec(init_method, new_globals, attrs)
        # Store the metaclass-generated __init__ for potential use by custom __init__
        metaclass_init = attrs["__init__"]
        
        result_class = super().__new__(cls, name, bases, attrs, **kwargs)
        
        # Store the metaclass-generated __init__ on the class so custom __init__ can call it
        result_class.__model_init__ = metaclass_init

        # Restore custom __init__ if it was defined
        # The custom __init__ should call self.__model_init__() to properly initialize fields
        if custom_init is not None:
            result_class.__init__ = custom_init

        # set fields' model class
        for k, default_v in (result_class.__fields__).items():
            default_v._set_model_cls(
                typing.cast(typing.Type["BaseModel"], result_class), 
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
    def init_ivars(ins: "BaseModel"):
        """Initialize instance variables
        """
        for k, default_v in BFModelMetaclass.__builtin_ivars__.items():
            setattr(ins, k, default_v() if callable(default_v) else default_v)

    @staticmethod
    def run_model_validators(ins: "BaseModel"):
        for validator in ins.__model_validators__:
            validator(ins)

    @staticmethod
    def run_after_field_validators(ins: "BaseModel"):
        for _ in range(len(ins.__after_field_validators__)):
            validator = ins.__after_field_validators__.pop(0)
            validator(value=ins[validator._field], model_ins=ins)


TV = typing.TypeVar("TV")


class BaseModel(metaclass=BFModelMetaclass):
    """BF Base Model - Base data model class

    Responsibilities
    ----------------
    - Describes the structure and constraints of data
    - Provides data validation through validators
    - Manages field instances and their metadata
    - Provides convenient API for data access
    
    Serialization
    -------------
    Use ModelConverter to serialize or deserialize a model::
    
        from blue_firmament.model.converter import ModelConverter
        
        converter = ModelConverter(User)
        result = converter.dump_to_dict(user_instance)
        
        # With field masks
        converter.register_mask_preset("public", (User.id, User.name))
        result = converter.dump_to_dict(user_instance, mask_preset="public")

    Partial
    ^^^^^^^
    Partial field will remain undefined if not provided during instantiation and
    no default value set, otherwise raise `ValueError`.

    Set `__partial__` to `True` to make all fields partial, you can override this
    in each field definition.
    """

    # class vars
    __key__: typing.ClassVar[Opt[Field]]  # TODO use field
    """Field that uniquely identifies an instance.

    Includes primary key, composite key.
    """
    __proxy__: typing.ClassVar[bool]
    """Proxy field value or not

    If disabled:
    - Mutable field value modification will not be tracked
    - Cannot get model or field info from field value
    """
    __fields__: typing.ClassVar[typing.Dict[str, Field]]
    """Fields and their instances defined in the model
    """
    __private_fields__: typing.ClassVar[typing.Dict[str, PrivateField]]
    """Private fields and their instances defined in the model
    """
    __model_validators__: typing.ClassVar[typing.List[ModelValidator]]
    __after_field_validators__: typing.ClassVar[typing.List[FieldValidator]]
    """Field validators needed to be ran
    immediately after model instantiation
    """
    __partial__: typing.ClassVar[bool]
    """If True, all fields are partial
    """
    __inherit_validators__: typing.ClassVar[bool]
    """If False, model and field validators will not be inherited by
    sub model.
    """
    __default_edflags__: typing.ClassVar[Opt[set[str]]]
    __default_idflags__: typing.ClassVar[Opt[set[str]]]

    # instance vars
    __field_values__: typing.ClassVar[typing.Dict[str, typing.Any]]
    """Storing each field's value
    
    - Key is the field's in_model_name.
    """
    __dirty_fields__: typing.ClassVar[typing.Set[str]]
    """Which fields are modified since last dump

    - Exclude private fields.
    """
    __unset_fields__: typing.ClassVar[typing.Set[str]]
    """Fields that are not provided during instantiation

    - Exclude private fields
    - Instance variable
    """
    __instantiated__: typing.ClassVar[bool]
    """Whether the model is instantiated

    - Instance variable
    """

    def __post_init__(self) -> None:
        """数据模型实例化后执行的操作；可以被重写"""

    @staticmethod
    def _init_private_fields(obj: 'BaseModel', data: typing.Any):

        for k, v in obj.__private_fields__.items():
            if k in data:
                setattr(obj, k, v.convert(data[k]))
            else:
                setattr(obj, k, v.default_value)

    @classmethod
    def __from_parents__(cls, /, *parents: "BaseModel") -> typing.Self:
        """Instantiate this model from its parent models.

        Precondition:
        - Inherited fields' name unchanged.
        """
        from .converter import ModelConverter
        data = {}
        for parent in parents:
            converter = ModelConverter(parent.__class__)
            data.update(converter.dump_to_dict(parent))

        return cls(**data)

    def _mark_unset(
        self, field_: str | Field
    ) -> None:
        """Mark field as unset (not provided during instantiation)
        """
        if isinstance(field_, Field):
            self.__unset_fields__.add(field_.in_model_name)
        else:
            self.__unset_fields__.add(field_)

    def _mark_dirty(self, field_: str | Field) -> None:
        """Mark field as dirty (modified since last dump)
        """
        if isinstance(field_, str):
            field_ = self.__fields__[field_]
        self.__dirty_fields__.add(field_.name)

    @classmethod
    def _get_key_field(cls) -> Field:
        """
        :raise KeyError: if no key on model
        """
        if not cls.__key__:
            raise KeyError(f'{cls.__name__} does not have a key')
        return cls.__key__

    @classmethod
    def _try_get_key_field(cls) -> Opt[Field]:
        """Try to get key field, return None if not exists.
        """
        return cls.__key__ if cls.__key__ else None
    
    # def dump(self, target_type: typing.Type[TV]) -> TV:
    #     """Serialize
    #     """
    #     if target_type is str:
    #         return self.dump_to_str()
    #     elif target_type is dict:
    #         return self.dump_to_dict()

    def __str__(self):
        from .converter import ModelConverter
        converter = ModelConverter(self.__class__)
        return converter.dump_to_str(self)
    
    def keys(self):
        """Return field names, enabling dict(model) conversion."""
        return self.__fields__.keys()
    
    def __iter__(self):
        """Iterate over field names, enabling dict(model) conversion."""
        return iter(self.__fields__.keys())
    
    def __len__(self):
        """Return number of fields."""
        return len(self.__fields__)

    def __getitem__(self, key: str | Field) -> typing.Any:
        """通过字段名/字段获取字段值

        Note: 不可以是其他属性，只可以是字段
        """
        if key in self.__fields__:
            return getattr(self, dump_field_name(key, in_model=True))
        
        raise KeyError(f'{key} is not a field of {self.__class__.__name__}')
    
    def __setitem__(self, key: str | Field, value: typing.Any) -> None:
        """通过字段/字段名设置字段值

        Note: 不可以是其他属性，只可以是字段
        """
        field = self.__fields__[dump_field_name(key)]
        field.__set__(self, value)

    @classmethod
    def keys(cls) -> typing.Iterable[str]:
        return cls.__fields__.keys()
    
    def values(self) -> typing.Iterable[typing.Any]:
        return self.__field_values__.values()
    
    FieldValueType = typing.TypeVar("FieldValueType")

    def _set_value(
        self, 
        field: Field[FieldValueType], 
        value: "FieldValueProxy[FieldValueType]" | FieldValueType | Undefined
    ) -> None:
        """设置字段值

        :param field: 字段名或字段实例
        """
        self.__field_values__[field.in_model_name] = value

    def _get_value(
        self,
        field: Field[FieldValueType]
    ) -> "FieldValueProxy[FieldValueType]" | FieldValueType:
        """获取字段值

        :param field: 字段名或字段实例
        """
        return self.__field_values__[field.in_model_name]

    def _merge(self, model: "BaseModel") -> None:
        """Merge current model with another model's values.

        Use ``dump_to_dict`` to get the values of the other model.

        :param model: The model to update from
        """
        if not isinstance(model, BaseModel):
            raise TypeError(f"Expected BaseModel, got {type(model)}")

        from .converter import ModelConverter
        converter = ModelConverter(model.__class__)
        dumped = converter.dump_to_dict(model)
        for field_name, value in dumped.items():
            self.__fields__[field_name].__set__(self, value)


# Aliases for new naming
BFModel = BaseModel
ModelTV = typing.TypeVar('ModelTV', bound=BaseModel)
"""Model type variable"""


class NoProxyModel(BaseModel, proxy=False):
    """Model with proxy disabled"""
    pass


class BaseRootModel(BaseModel):
    """Root Model class

    - Has only one root field
    - When serializing, root won't be used as field name
    """
    root: Field


def merge(model1: BaseModel, model2: BaseModel) -> None:
    """Merge same fields (by name)'s value from model2 to model1.

    Will firstly dump model2 (so partial will not be included)

    Examples
    --------
    >>> merge(ModelA(a=1, b=3), ModelB(a=2))
    ModelA: a=2, b=3
    >>> merge(ModelA(a=1), ModelB(a=_undefined))
    ModelB: a=1
    """
    from .converter import ModelConverter
    converter = ModelConverter(model2.__class__)
    for field_ in converter.dump_to_dict(model2):
        try:
            model1[field_] = model2[field_]
        except KeyError:
            continue

