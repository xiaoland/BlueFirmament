
import typing

from .validator import BaseValidator, get_validator_by_type

class UndefinedValue:

    """未定义值
    """
    
    def __repr__(self):
        return 'BlueFirmamentUndefined'
    
    @classmethod
    def is_(cls, value: typing.Any) -> typing.TypeGuard['UndefinedValue']:
        """判断值是否为未定义值
        """
        return value is cls()
    
    def __bool__(self) -> bool:
        return False


FieldValueType = typing.TypeVar('FieldValueType')
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
        is_primary_key: bool = False,
        validator: typing.Optional[typing.Callable[[typing.Any], FieldValueType]] = None,
    ):

        """
        Parameters
        ^^^
        - `default`: 默认值；初始化时若未提供该字段的值则使用此默认值；实例化之后不可修改
        - `name`：字段名；与数据访问层交互该字段时使用该名称；实例化之后不可修改
        - `default_factory`：默认值工厂；默认值需要动态生成或者为可变对象时使用，应该是一个可调用对象
        - `is_primary_key`：是否为主键；默认为假
        - `validator`：校验器；数据模型将用此校验字段值
        """
        self.__name = name
        self.__default = default
        self.__default_factory = default_factory
        self.__is_primary_key = is_primary_key
        self.__validator = validator

    def fork(self, 
        default: UndefinedValue | FieldValueType = UndefinedValue(),
        default_factory: typing.Optional[typing.Callable[[], FieldValueType]] = None,
        name: typing.Optional[str] = None,
        is_primary_key: bool = False,
        validator: typing.Optional[typing.Callable[[typing.Any], FieldValueType]] = None         
    ) -> typing.Self:

        """克隆字段实例
        """
        return self.__class__(
            default=default if not isinstance(default, UndefinedValue) else self.__default,
            default_factory=default_factory or self.__default_factory,
            name=name or self.__name,
            is_primary_key=is_primary_key or self.__is_primary_key,
            validator=validator or self.__validator,
        )

    @property
    def name(self) -> str: 
        if self.__name is None:
            raise ValueError('Field name is not defined')
        return self.__name
    
    def _set_name(self, value: str, no_raise: bool = False) -> None:
        """设置字段名称

        如果已经设置过名称，则抛出错误；如果不想抛出错误，则传入 ``no_raise`` 参数为 ``True``
        """
        if self.__name is not None:
            if no_raise:
                return None
            raise ValueError('Field name is immutable')
        self.__name = value

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
        elif not isinstance(self.__default, UndefinedValue):
            return self.__default
        else:
            raise ValueError('No default value provided for field')



T = typing.TypeVar('T')
def Field(
    default: T | UndefinedValue = UndefinedValue(), 
    default_factory: typing.Optional[typing.Callable[[], T]] = None,
    name: typing.Optional[str] = None,
    is_primary_key: bool = False,
    validator: typing.Optional[BaseValidator] = None
) -> typing.Any:
    
    return BlueFirmamentField[T](
        default=default, 
        default_factory=default_factory, 
        name=name, 
        is_primary_key=is_primary_key, 
        validator=validator
    )

class BlueFirmamentPrivateField(BlueFirmamentField):

    """碧霄私有字段

    私有字段扮演实例变量的角色
    """
    pass


def PrivateField(
    default: T | UndefinedValue = UndefinedValue(),
    default_factory: typing.Optional[typing.Callable[[], T]] = None,
    name: typing.Optional[str] = None,
    is_primary_key: bool = False,
    validator: typing.Optional[BaseValidator] = None
) -> typing.Any:
    
    return BlueFirmamentPrivateField(
        default=default, 
        default_factory=default_factory, 
        name=name, 
        is_primary_key=is_primary_key, 
        validator=validator
    )


def field_as_class_var(field: T) -> T:

    '''将字段当作类变量使用

    传入字段实例，返回字段实例的默认值
    '''
    return typing.cast(BlueFirmamentField[T], field).default_value
