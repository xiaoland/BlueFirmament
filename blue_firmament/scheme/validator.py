

import typing
import enum

from ..utils.type import safe_issubclass
from ..utils import singleton

if typing.TYPE_CHECKING:
    from .main import BaseScheme


ValidateResultType = typing.TypeVar('ValidateResultType')
ValidatorModeType = typing.Literal['base'] | typing.Literal['strict']
class BaseValidator(typing.Generic[ValidateResultType]):
    
    """碧霄校验器基类

    Usage
    ^^^
    - 调用并传入需要校验的值，如果不通过将抛出ValueError，否则返回值

    Features
    ^^^
    - 可以设置校验模式：`base`, `strict`
        - `base`：即便类型不匹配，仍然尝试转换为目标类型，成功则视为通过并返回转换值
        - `strict`：类型不匹配则直接抛出异常
        - 子校验器不在初始化器中接受该参数，可以在调用或者直接修改mode属性来设置
    """

    def __init__(self, mode: ValidatorModeType = 'base') -> None:
        
        super().__init__()

        self.mode = mode

    def __call__(self, value) -> ValidateResultType:
        
        raise NotImplementedError('`__call__` method must be implemented in subclass')
    @property
    @abc.abstractmethod
    def type(self) -> typing.Type[ValidateResultType]:
        ...


# BUG type problem to solve
BaseSchemeType = typing.TypeVar('BaseSchemeType', bound="BaseScheme")
EnumType = typing.TypeVar('EnumType', bound=enum.Enum)
@typing.overload
def get_validator_by_type(  # type: ignore
    type: typing.Type["BaseSchemeType"]
) -> typing.Type[BaseSchemeType]:
    ...
@typing.overload
def get_validator_by_type(
    type: typing.Type[EnumType]
) -> typing.Type[EnumType]:
    ...
@typing.overload
def get_validator_by_type(  # type: ignore
    type: typing.Type
) -> BaseValidator:
    ...
def get_validator_by_type(
    type: typing.Union[
        typing.Type, typing.Type[BaseSchemeType],
        typing.Type[EnumType]
    ]
) -> typing.Union[
    BaseValidator, 
    typing.Type[BaseSchemeType],
    typing.Type[EnumType]
]:
    
    """根据类型获取校验器

    Behaviour
    ---------
    - 找不到合适的校验器则返回通用校验器
    - 如果是 enum 的子类，则返回 enum 本身
    - 如果是 BaseScheme 的子类，则返回本身
    """
    from .main import BaseScheme
    if safe_issubclass(type, BaseScheme):
        return type  # type: ignore
    if safe_issubclass(type, enum.Enum):
        return type  # type: ignore
    if type is int:
        return IntValidator()
    
    return AnyValidator()



@singleton
class AnyValidator(BaseValidator[typing.Any]):
    
    """
    通用校验器（原样返回）；全局唯一实例
    """
    def __call__(self, value: typing.Any) -> typing.Any: 
        return value


class IntValidator(BaseValidator[int]):
    
    """整型校验器

    可以校验的内容
    ^^^^^^^^^^^^^^
    - 数值范围
    - 奇偶性
    """

    def __init__(self, min: int | None = None, max: int | None = None):
        
        super().__init__()

        self.min = min
        self.max = max

    def __call__(self, value: typing.Any) -> int:
        
        res = int(value)
        if self.min is not None and res < self.min:
            raise ValueError(f'Value {res} is less than minimum {self.min}')
        if self.max is not None and res > self.max:
            raise ValueError(f'Value {res} is greater than maximum {self.max}')
        return res
