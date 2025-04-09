

import typing

from ..utils import singleton


ValidatorModeType = typing.Literal['base'] | typing.Literal['strict']

ValidateResultType = typing.TypeVar('ValidateResultType')
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


def get_validator_by_type(type: typing.Any) -> BaseValidator:
    
    """根据类型获取校验器

    Behaviour
    ---------
    - 找不到合适的校验器则返回通用校验器
    """
    if type == int:
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
