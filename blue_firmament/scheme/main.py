import inspect
import typing
import types

from ..dal import DALPath
from ..dal.filters import EqFilter
from .field import (
    BlueFirmamentPrivateField, BlueFirmamentField, dump_field_name
)
from .field import UndefinedValue, FieldValueProxy


@typing.dataclass_transform(kw_only_default=True)
class SchemeMetaclass(type):

    """碧霄数据模型元类

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

    # if typing.TYPE_CHECKING:
    __builtin_fields__: typing.Iterable[str]
    '''碧霄数据模型的内置字段；必须是``_<name>``形式'''
    __fields__: typing.Dict[str, BlueFirmamentField]
    '''数据模型的字段字典；键为字段名，值为字段实例'''
    __private_fields__: typing.Dict[str, BlueFirmamentPrivateField]
    '''数据模型的私有字段字典；键为字段名，值为私有字段实例'''
    __field_values__: typing.Dict[str, typing.Any]
    '''数据模型的字段值字典；键为字段名，值为字段值；包括私有字段'''
    __dirty_fields__: typing.Set[str]
    '''数据模型的脏字段集合；不包括私有字段'''
    __table_name__: typing.Optional[str] = None
    '''表名'''
    __schema_name__: typing.Optional[str] = None
    '''表组名'''
    __proxy__: bool = False
    '''是否对字段值进行代理'''

    __builtin_fields__ = ('_table_name', '_schema_name', '_proxy')
    

    def __new__(
        cls, name: str, bases: typing.Tuple[type[typing.Any], ...], attrs: typing.Dict[str, typing.Any]
    ):

        # 排除非数据模型类
        if name in ("BaseScheme",):
            return super().__new__(cls, name, bases, attrs)

        # 处理内置字段
        for field in cls.__builtin_fields__:
            if field in attrs:
                attrs[f'_{field}__'] = attrs[field]
                del attrs[field]
            else:
                attrs[f'_{field}__'] = None
        
        # 解析字段定义
        fields: typing.Dict[str, BlueFirmamentField] = dict()
        private_fields: typing.Dict[str, BlueFirmamentPrivateField] = dict()
        # 解析父类的字段定义
        if bases:
            for base in bases:
                if hasattr(base, '__fields__'):
                    forked_fields = {
                        k: v.fork()
                        for k, v in typing.cast(
                            typing.Dict[str, BlueFirmamentField],
                            base.__fields__
                        ).items()
                    }
                    fields.update(forked_fields)
                if hasattr(base, '__private_fields__'):
                    forked_private_fields = {
                        k: v.fork()
                        for k, v in typing.cast(
                            typing.Dict[str, BlueFirmamentPrivateField],
                            base.__private_fields__
                        ).items()
                    }
                    private_fields.update(forked_private_fields)

        # 解析当前类的字段定义
        for k, v in attrs.items():

            # 跳过魔法属性（根据名称调过）
            if k.startswith('__') and k.endswith('__'):
                continue

            # 跳过方法
            if inspect.ismethoddescriptor(v):
                continue
            elif inspect.isfunction(v):
                continue

            # 跳过property
            if isinstance(v, property):
                continue

            # 解析私有字段实例
            if isinstance(v, BlueFirmamentPrivateField):
                private_fields[k] = v
                v._set_name(k, True) # 如果没有配置名称，则使用类变量名作为字段名
                v._set_in_scheme_name(k, True)
                continue

            # 解析为字段实例
            if isinstance(v, BlueFirmamentField):
                fields[k] = v
                v._set_name(k, True) # 如果没有配置名称，则使用类变量名作为字段名
                v._set_in_scheme_name(k, True)
            else:
                
                if k in fields:
                    fields[k] = fields[k].fork(
                        default=v, name=k, in_scheme_name=k,
                    )
                    continue
                elif k in private_fields:  # `elif`: 不可能又私有又普通的
                    private_fields[k] = private_fields[k].fork(
                        default=v, name=k, in_scheme_name=k
                    )
                    continue

                fields[k] = BlueFirmamentField(v, name=k, in_scheme_name=k)

        # 根据类型注解设置校验器
        for k, v in (fields | private_fields).items():
            anno = attrs.get('__annotations__', {}).get(k)
            if anno:
                v.set_validator_from_type(anno)

        # 处理没有值，只有类型注解的字段
        cls_annotations = attrs.get('__annotations__', {})
        for k, v in cls_annotations.items():

            # 跳过魔法属性
            if k.startswith('__') and k.endswith('__'):
                continue

            if k not in fields and k not in private_fields:
                fields[k] = BlueFirmamentField(default=UndefinedValue(), name=k)
                fields[k].set_validator_from_type(v)

        # # 替换识别到的字段、私有字段值为字段实例
        for k, v in (fields | private_fields).items():
            attrs[k] = v
        
        attrs['__fields__'] = fields
        attrs['__private_fields__'] = private_fields

        # 生成 __init__ 方法
        init_params = []
        init_assignments = []
        new_globals = globals().copy()
        for k, v in (fields | private_fields).items():
            type_: typing.Type | types.UnionType | None = cls_annotations.get(k, None)
            if type_ is None:
                type_str = 'typing.Any'
            elif isinstance(type_, types.UnionType):
                type_str = '|'.join([t.__name__ for t in type_.__args__])
                type_str = type_str.replace('NoneType', 'None')
            else:
                type_str = type_.__name__
                new_globals[type_str] = type_

            init_params.append(f"{k}: {type_str} = UndefinedValue()")
            init_assignments.append(f"    self.{k} = {k}")  # self.k is a field instance (descriptor)
        
        if init_params:
            init_sig = f"def __init__(self, *, {', '.join(init_params)}, **kwargs):\n"
        else:
            init_sig = f"def __init__(self, **kwargs):\n"
        init_body = '    self.__field_values__ = dict()\n'
        init_body += '    self.__dirty_fields__ = set()\n'
        init_body += '\n'.join(init_assignments)
        init_body += '\n    self.__post_init__()\n'

        init_method = init_sig + init_body
        
        exec(init_method, new_globals, attrs)

        result_class = super().__new__(cls, name, bases, attrs)

        # set fields' scheme
        for k, v in (result_class.__fields__ | result_class.__private_fields__).items():
            v._set_scheme_cls(
                typing.cast(typing.Type["BaseScheme"], result_class), 
                no_raise=True, force=True
            )

        return result_class


class BaseScheme(metaclass=SchemeMetaclass):

    """碧霄（基本）数据模型类

    Features
    ---------
    实例化与校验
    ^^^^^^^^^^^^^^
    
    序列化
    ^^^^^^^
    - ``dump_to_dict``：序列化为字典
    - ``**MyScheme``: 
        - 通过 `__getitem__` 方法获得所需要的字段，场景 ``f(**MyScheme)``
        - 通过 `keys()` + `__getitem__` 方法，场景 ``{**MyScheme, 'other_field': 1}``

    与数据访问层交互
    ^^^^^^^^^^^^^^^^^
    - 将数据模型类传递给DAO的获取方法，可以获得数据模型实例
    - 将数据模型类和字段实例传递给DAO的获取、插入、更新方法，可以相应地操作该字段
    - 将数据模型类和主键字段实例传递给DAO地获取、插入、更新、删除方法，可以相应地操作该数据模型
    - 将数据模型实例传递给DAO的插入、更新、删除方法，可以相应地操作该数据模型
    - 也可以通过数据模型的类方法和实例方法操作数据模型
        - ``from_insert`` ：从字典插入数据并实例化
        - ``insert`` ：插入数据模型实例到数据持久层
        - ``update`` ：更新数据持久层中的数据模型实例
        - ``delete`` ：从数据持久层删除整个记录

    字段与数据
    ^^^^^^^^^^
    - ``实例.字段名（类变量名）`` 访问字段值
    - 使用 ``get_scheme_field(Scheme, field_name)`` 来获取数据模型类的字段实例
    """

    def __post_init__(self) -> None:
        '''数据模型实例化后执行的操作；可以被重写'''
        pass

    @staticmethod
    def _init_private_fields(obj: 'BaseScheme', data: typing.Any):

        for k, v in obj.__private_fields__.items():
            if k in data:
                setattr(obj, k, v.validate(data[k]))
            else:
                setattr(obj, k, v.default_value)

    @classmethod
    def dal_path(cls) -> DALPath:
        return DALPath((cls.__table_name__, cls.__schema_name__))

    @classmethod
    def get_primary_key(cls) -> BlueFirmamentField:
        '''数据模型主键名称
        
        Behavior
        ^^^^^^^^
        - 遍历字段字典，返回标记为主键的字段的名称
        - 如果没有主键字段，则抛出KeyError异常
        '''
        for i in cls.__fields__.values():
            if i.is_primary_key:
                return i
            
        raise KeyError(f'No primary key found in {cls.__name__}')
    
    @property
    def primary_key_eqf(self) -> EqFilter:
        pri_key = self.get_primary_key()
        return EqFilter(
            pri_key, self[pri_key]
        )

    def dump_to_dict(self, 
        only_dirty: bool = False,
        exclude_primary_key: bool = False,
    ) -> dict:
        
        """序列化为字典

        :param only_dirty: 是否只序列化脏字段
        :param exclude_primary_key: 是否排除主键字段

        TODO
        ----
        - 应当使用字段的 dump_to_dict 方法来序列化字段
        - 提供 `jsonable` 选项指示是否确保输出的字典是 JSON 可序列化的
            - 需要特殊处理自定义类型

        Behaviour
        ----------
        - 如果开启 `__proxy__`，则调用 FieldValueProxy 的 dump 来获取原始值
        """
        data = dict()

        field_names: typing.Set[str] = set()
        if only_dirty:
            field_names = self.__dirty_fields__
        else:
            field_names = typing.cast(typing.Set[str], self.__fields__.keys())

        if exclude_primary_key:
            field_names = field_names - {self.get_primary_key().name}

        for k in field_names:
            data[k] = FieldValueProxy.dump(getattr(self, k))
        return data
    
    def dump(self) -> typing.Any:
        
        '''序列化
        
        将本数据模型实例序列化为该数据模型推荐的格式
        '''
    
    def __getitem__(self, key: str | BlueFirmamentField) -> BlueFirmamentField:
        
        """通过字段名/字段获取字段值

        Note: 不可以是其他属性，只可以是字段
        """
        if key in self.__fields__:
            return getattr(self, dump_field_name(key))
        
        raise KeyError(f'{key} is not a field of {self.__class__.__name__}')
    
    def __setitem__(self, key: str | BlueFirmamentField, value: typing.Any) -> None:

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

    def set_value(
        self, field: BlueFirmamentField[FieldValueType], 
        value: "FieldValueProxy[FieldValueType]" | FieldValueType
    ) -> None:

        """设置字段值

        :param field: 字段名或字段实例
        """
        self.__field_values__[field.in_scheme_name] = value

    def get_value(
        self, field: BlueFirmamentField[FieldValueType]
    ) -> "FieldValueProxy[FieldValueType]" | FieldValueType:

        """获取字段值

        :param field: 字段名或字段实例
        """
        return self.__field_values__[field.in_scheme_name]

    @classmethod
    def get_partial(cls):
        return make_partial(cls)
    
    def mark_dirty(self, field: str | BlueFirmamentField) -> None:

        """标记字段为脏字段

        :param field: 字段名或字段实例
        """
        if isinstance(field, str):
            field = self.__fields__[field]
        self.__dirty_fields__.add(field.name)


def make_partial(cls: typing.Type[BaseScheme]):

    '''转化数据模型类为部分化数据模型类

    部分化数据模型类有下列特性：
    - 缺失的字段不会被赋值为默认值，而是被赋值为 ``BlueFirmamentUndefinedValue``
    - 缺失的字段会记录在 ``__partial_fields__`` 属性中
    - 序列化时会忽略 ``__partial_fields__`` 中的字段

    缺点：
    - 不与类型提示对齐

    TODO
    ^^^^
    - 
    '''

    class PartialScheme(cls):

        _schema_name = cls.__schema_name__
        _table_name = cls.__table_name__

        def __init__(self, /, **kwargs: typing.Any):

            self.__partial_fields: typing.Set[str] = set()
            '''缺失的字段'''
            
            for k, v in self.__fields__.items():
                if k in kwargs:
                    setattr(self, k, v.validate(kwargs[k]))
                else:
                    setattr(self, k, UndefinedValue)
                    self.__partial_fields |= {k}

            # 初始化私有字段
            self._init_private_fields(self, kwargs)

        def dump_to_dict(self, 
            only_dirty: bool = False,
            exclude_primary_key: bool = False,
        ) -> dict:

            data = dict()

            if only_dirty:
                field_names = self.__dirty_fields__
            else:
                field_names = self.__fields__.keys() - self.__partial_fields

            if exclude_primary_key:
                field_names = field_names - {self.get_primary_key().name}

            for k in field_names:
                data[k] = getattr(self, k)  
            return data

    PartialScheme.__name__ = f'Partial{cls.__name__}'

    return PartialScheme

