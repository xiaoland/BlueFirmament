"""BlueFirmament Scheme's Validator module.

:doc:`/design/scheme/validator`
"""

__all__ = [
    "BaseValidator",
    "FieldValidator",
    "field_validator",
]

import abc
import typing
from typing import Optional as Opt, Annotated as Anno, Literal as Lit


from ..utils import call_function, is_instance_method_by_signature

if typing.TYPE_CHECKING:
    from .field import BlueFirmamentField
    from .main import BaseScheme


T = typing.TypeVar("T")
BaseSchemeTV = typing.TypeVar("BaseSchemeTV", bound="BaseScheme")
class BaseValidator(abc.ABC, typing.Generic[T]):

    @abc.abstractmethod
    def __call__(self, value: T, **kwargs) -> None:

        """Validate the value.

        :param value: The value to validate.
        :raises ValueError: If the value is invalid.
        """


class FieldValidator(BaseValidator[T], typing.Generic[T]):

    """Validator for a field.

    This validator will be added to the field once instantiated.
    """

    FuncT = typing.Union[
        # def func(value: Any) -> None
        typing.Callable[[typing.Any], 
            typing.Union[
                None, 
                typing.Coroutine[None, None, None]
            ]
        ],
        # await def func(self: BaseScheme, value: Any) -> None
        typing.Callable[
            [BaseSchemeTV, typing.Any], 
            typing.Union[
                None, 
                typing.Coroutine[None, None, None]
            ]
        ],
    ]
    """Callable types that FieldValidator can accept.
    """

    def __init__(self, 
        field: "BlueFirmamentField",
        func: FuncT,
    ) -> None:
        
        """
        :param field: The field to validate.
        :param func: The function to call to validate the field.

            Supports:
            - def func(value: Any) -> None
            - async def func(value: Any) -> None
            - def func(self: BaseScheme, value: Any) -> None
            - async def func(self: BaseScheme, value: Any) -> None
        """
        
        self.__func = func
        self.__is_instance_method = is_instance_method_by_signature(func)
        field._add_validator(self)

    def __call__(self, 
        value: typing.Any,
        scheme_ins: Opt["BaseScheme"] = None,
        **kwargs
    ) -> None:
        
        """
        :param scheme_ins: If func is instance method, provide the instance.
        """
        if self.__is_instance_method:
            return call_function(
                self.__func, scheme_ins, value
            )
        else:
            return call_function(self.__func, value)


def field_validator(
    field: "BlueFirmamentField[T]"
): 
    
    """Decorator to create a field validator.

    :param field: The field to validate.

    Examples
    --------
    .. code-block:: python
        
        from blue_firmament.scheme import field_validator
        from blue_firmament.scheme import BaseScheme

        class Post(BaseScheme):
            __table_name__ = "post"
            
            _id: int
            status: FieldT(str) = Field("open")

        class Comment(BaseScheme):
            __table_name__ = "comment"
            
            post: FieldT[int] = Field()
            ...

            @field_validator(post)
            async def post_is_open(self, value: int):
                post_status = self.dao.select_one(Post.status, value)
                if post_status != "open":
                    raise ValueError("Post is not open")
            
        
    """

    def wrapper(func: 
        typing.Union[
            typing.Callable[[T], 
                typing.Union[
                    None, 
                    typing.Coroutine[None, None, None]
                ]
            ],
            typing.Callable[
                [BaseSchemeTV, T], 
                typing.Union[
                    None, 
                    typing.Coroutine[None, None, None]
                ]
            ],
        ]       
    ) -> FieldValidator[T]:
        return FieldValidator(field, func)

    return wrapper
