"""BlueFirmament Scheme's Validator module.

:doc:`/design/scheme/validator`
"""

__all__ = [
    "BaseValidator",
    "FieldValidator",
    "field_validator",
]

import abc
import copy
import typing
from typing import Optional as Opt, Annotated as Anno, Literal as Lit

from .._types import Undefined, _undefined
from ..utils import call_function

if typing.TYPE_CHECKING:
    from .field import Field
    from .main import BaseScheme
    from ..log.main import LoggerT


T = typing.TypeVar("T")
BaseSchemeTV = typing.TypeVar("BaseSchemeTV", bound="BaseScheme", contravariant=True)
class BaseValidator(abc.ABC, typing.Generic[T]):

    """Base class for validators.
    """

    @abc.abstractmethod
    def _get_logger(self, *args, **kwargs) -> "LoggerT":

        """Validator level logger.

        Logger binded to validator context
        """

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

    class InstanceMethodFunc(typing.Protocol[BaseSchemeTV]):
        def __call__(_, self: BaseSchemeTV, value: typing.Any) -> typing.Union[
            None, typing.Coroutine[None, None, None]
        ]:
            ...
            
    FuncT = typing.Union[
        InstanceMethodFunc
    ]
    """Function types that FieldValidator can accept.
    """

    def __init__(self, 
        field: "Field",
        func: FuncT,
        mode: Lit["before", "after"] = "after",
    ) -> None:
        
        """
        :param field: The field to validate.
        :param func: The function to call to validate the field.
        :param mode: 
            ``before``: validate before scheme instantiated.
            ``after``: validate after scheme instantiated.
        """
        
        self.__func = func
        self._field = field
        self.__mode = mode

        self._field._add_validator(self)

    def _get_logger(self,
        scheme_ins: "BaseScheme",
    ):
        """Get validator level logger
        """
        return scheme_ins._logger.bind(
            validator_func=self.__func.__qualname__,
        )

    def __call__(self, 
        value: typing.Any,
        scheme_ins: "Undefined | BaseScheme" = _undefined,
        force: bool = False,
        **kwargs
    ) -> None:
        
        """
        :param scheme_ins: If func is instance method, provide the instance.
        :param force: 
            If True, bypass mode check
        """
        if scheme_ins is _undefined:
            raise ValueError(
                "using instance method, but no scheme instance provided"
            )
        if not force:
            if self.__mode == "after":
                if not scheme_ins.__instantiated__:
                    scheme_ins.__after_field_validators__.append(self)
                    return None
        
        logger = self._get_logger(scheme_ins=scheme_ins)

        # log extrance
        logger.info("Enter field validator", 
            field_name=self._field.in_scheme_name, value=value
        )
        
        scheme_ins_copy = copy.copy(scheme_ins)
        scheme_ins_copy._set_logger(logger)
        call_function(self.__func, scheme_ins_copy, value)


def field_validator(
    field: "Field[T]",
    mode: Lit["before", "after"] = "after",
): 
    """Decorator to create a field validator.

    :param field: The field to validate.

    Examples
    --------
    .. code-block:: python
        
        from blue_firmament.scheme import field_validator
        from blue_firmament.scheme import BaseScheme

        class Post(BaseScheme):
            __dal_path__ = ("post",)
            
            _id: int
            status: FieldT(str) = Field("open")

        class Comment(BaseScheme):
            __dal_path__ = ("comment",)
            
            post: FieldT[int] = Field()
            ...

            @field_validator(post)
            async def post_is_open(self, value: int):
                post_status = self.dao.select_one(Post.status, value)
                if post_status != "open":
                    raise ValueError("Post is not open")
            
        
    """
    def wrapper(func: FieldValidator.FuncT) -> FieldValidator[T]:
        """
        :param func: The function to call to validate the field.

            Supports:
            - ``def func(value: Any) -> None``
            - ``async def func(value: Any) -> None``
            - ``def func(self: BaseScheme, value: Any) -> None``
            - ``async def func(self: BaseScheme, value: Any) -> None``
        """
        return FieldValidator(field=field, func=func, mode=mode)

    return wrapper


def field_validators(
    *fields: "Field",
    mode: Lit["before", "after"] = "after",
):
    def wrapper(func: FieldValidator.FuncT) -> typing.List[FieldValidator]:
        """
        :param func: The function to call to validate the field.

            Supports:
            - ``def func(value: Any) -> None``
            - ``async def func(value: Any) -> None``
            - ``def func(self: BaseScheme, value: Any) -> None``
            - ``async def func(self: BaseScheme, value: Any) -> None``
        """
        res = []
        for field in fields:
            res.append(FieldValidator(field=field, func=func, mode=mode))
        return res

    return wrapper


class SchemeValidator(BaseValidator):

    """Validator for a scheme.

    This validator will be added to the scheme when creating class.
    """

    class InstanceMethodFunc(typing.Protocol[BaseSchemeTV]):
        def __call__(_, self: BaseSchemeTV) -> typing.Union[
            None, typing.Coroutine[None, None, None]
        ]:
            ...

    FuncT = typing.Union[
        InstanceMethodFunc
    ]
    """Function types that SchemeValidator can accept.
    """

    def __init__(self, 
        func: FuncT,
    ) -> None:
        
        """
        :param func: The function to call to validate the scheme.
        """
        self.__func = func

    def _get_logger(self,
        scheme_ins: "BaseScheme",
    ):
        return scheme_ins._logger.bind(
            validator_func=self.__func.__qualname__,
        )

    def __call__(self, 
        scheme_ins: "BaseScheme",
        **kwargs
    ) -> None:
        
        """
        :param scheme_ins: The scheme instance to validate.
        """
        logger = self._get_logger(scheme_ins=scheme_ins)

        # log extrance
        logger.info("Enter scheme validator", 
            scheme_name=scheme_ins.__class__.__name__, value=scheme_ins.dump_to_dict()
        )

        scheme_ins_copy = copy.copy(scheme_ins)
        scheme_ins_copy._set_logger(logger)
        call_function(self.__func, scheme_ins_copy)


def scheme_validator(func: SchemeValidator.FuncT) -> SchemeValidator:
    """Decorator to create a scheme validator.

    :param func: The function to call to validate the scheme.

        Supports:
        - ``def func(self: BaseScheme) -> None``
        - ``async def func(self: BaseScheme) -> None``

    """
    return SchemeValidator(func)
