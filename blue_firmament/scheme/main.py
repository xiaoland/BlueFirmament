import inspect
import types
import typing
from .field import BlueFirmamentPrivateField, BlueFirmamentField
from .field import UndefinedValue

if typing.TYPE_CHECKING:
    from ..dal import DataAccessObject


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

    if typing.TYPE_CHECKING:
        __builtin_fields__: typing.Iterable[str]
        '''碧霄数据模型的内置字段；必须是``_<name>``形式'''
        __fields__: typing.Dict[str, BlueFirmamentField]
        '''数据模型的字段字典；键为字段名，值为字段实例'''
        __private_fields__: typing.Dict[str, BlueFirmamentPrivateField]
        '''数据模型的私有字段字典；键为字段名，值为私有字段实例'''
        __table_name__: typing.Optional[str] = None
        '''表名'''
        __schema_name__: typing.Optional[str] = None
        '''表组名'''

    __builtin_fields__ = ('_table_name', '_schema_name')
    

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
                    fields.update(base.__fields__)
                if hasattr(base, '__private_fields__'):
                    private_fields.update(base.__private_fields__)

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
                v._set_name(k) # 如果没有配置名称，则使用类变量名作为字段名
                continue

            # 解析为字段实例
            if isinstance(v, BlueFirmamentField):
                fields[k] = v
                v._set_name(k) # 如果没有配置名称，则使用类变量名作为字段名
            else:
                
                if k in fields:
                    fields[k] = fields[k].fork(
                        default=v, name=k
                    )
                    continue
                elif k in private_fields:  # `elif`: 不可能又私有又普通的
                    private_fields[k] = private_fields[k].fork(
                        default=v, name=k
                    )
                    continue

                fields[k] = BlueFirmamentField(v, name=k)

        # 根据类型注解设置校验器
        for k in fields.keys():
            anno = attrs.get('__annotations__', {}).get(k)
            if anno:
                fields[k].set_validator_from_type(anno)
        for k in private_fields.keys():
            anno = attrs.get('__annotations__', {}).get(k)
            if anno:
                private_fields[k].set_validator_from_type(anno)

        # 处理没有值，只有类型注解的字段
        for k, v in attrs.get('__annotations__', {}).items():

            # 跳过魔法属性
            if k.startswith('__') and k.endswith('__'):
                continue

            if k not in fields and k not in private_fields:
                fields[k] = BlueFirmamentField(default=UndefinedValue, name=k)
                fields[k].set_validator_from_type(v)
        
        attrs['__fields__'] = fields
        attrs['__private_fields__'] = private_fields

        return super().__new__(cls, name, bases, attrs)


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

    def __init__(self, /, **data: typing.Any):
            
        # 初始化普通字段
        for k, v in self.__fields__.items():
            if k in data:
                setattr(self, k, v.validate(data[k]))
            else:
                setattr(self, k, v.default_value)

        # 初始化私有字段
        self._init_private_fields(self, data)

        self.__post_init__()

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
    def get_primary_key(cls) -> str:
        '''数据模型主键名称
        
        Behavior
        ^^^^^^^^
        - 遍历字段字典，返回标记为主键的字段的名称
        - 如果没有主键字段，则抛出KeyError异常
        '''
        for i in cls.__fields__.values():
            if i.is_primary_key:
                return i.name
            
        raise KeyError(f'No primary key found in {cls.__name__}')
    
    @property
    def primary_key_value(self) -> typing.Any:
        '''
        Exception
        ^^^^^^^^^^^^
        - ``KeyError``：没有主键字段
        '''
        return getattr(self, self.get_primary_key())

    def dump_to_dict(self) -> dict:
        
        """序列化为字典
        """
        data = dict()
        for k in self.__fields__.keys():
            data[k] = getattr(self, k)
        return data
    
    def dump(self) -> typing.Any:
        
        '''序列化
        
        将本数据模型实例序列化为该数据模型推荐的格式
        '''
    
    def __getitem__(self, key: str) -> typing.Any:
        
        """通过字段名获取字段值

        不可以是其他属性，只可以是字段
        """
        if key in self.__fields__:
            return getattr(self, key)

    def keys(self) -> typing.Iterable[str]:
        
        """获取所有字段名
        """
        return self.__fields__.keys()

    @classmethod
    async def from_insert(cls, /, _dao = None, **kwargs) -> typing.Self:
        
        """插入数据模型到数据持久层（简易版）

        传入字段键值对作为数据模型的初始化参数并存储到数据持久层中，返回实例化的数据模型。

        特性
        ^^^^^
        - 不指定主键值则根据定义的主键类型自动生成
        """
        return cls(**kwargs)
    
    @classmethod
    async def from_primary_key(cls, primary_key_value, _dao: 'DataAccessObject') -> typing.Self:

        """基于主键实例化数据模型

        :param primary_key_value: 主键值；（没有校验主键值的类型与数据模型定义的主键类型一致）

        Warning
        ^^^^^^^
        推荐使用 ``DataAccessObject().select_a_scheme_from_primary_key`` 方法来获取数据模型实例而不是本方法 \n
        因为本方法要求调用者传入DAO，这增加了调用者的心智负担
        """
        raise NotImplementedError('cls.from_primary_key must be implemented by subclass')
    
    async def insert(self, _dao = None) -> None:
        
        """将当前数据实例插入到数据持久层中

        :param _dao: 数据访问对象；不传入则默认使用全局DAO
        """
        pass

    async def update(self, *fields, _dao = None) -> None:

        """更新数据持久层中的当前数据实例

        :param _dao: 数据访问对象；不传入则默认使用全局DAO
        """
        pass

    async def delete(self, _dao = None) -> None:
        
        """从数据持久层删除当前数据实例

        :param _dao: 数据访问对象；不传入则默认使用全局DAO
        """
        pass


def make_partial(cls: typing.Type[BaseScheme]):

    '''转化数据模型类为部分化数据模型类

    部分化数据模型类有下列特性：
    - 缺失的字段不会被赋值为默认值，而是被赋值为 ``BlueFirmamentUndefinedValue``
    - 缺失的字段会记录在 ``__partial_fields__`` 属性中
    - 序列化时会忽略 ``__partial_fields__`` 中的字段

    缺点：
    - 不与类型提示对齐
    '''

    class PartialScheme(cls):

        __name__ = f'Partial{cls.__name__}'

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

        def dump_to_dict(self) -> dict:

            data = dict()
            for k in (self.__fields__.keys() - self.__partial_fields):
                data[k] = getattr(self, k)  
            return data

    return PartialScheme
