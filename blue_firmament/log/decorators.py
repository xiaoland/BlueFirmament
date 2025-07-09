"""Decorators for logging
"""

__all__ = [
    "log_manager_handler",
]

import copy
import inspect
import functools
import typing
from typing import Optional as Opt, Annotated as Anno, Literal as Lit
from .._types import AnnotatedDirective as AD
from ..utils.typing_ import is_annotated, get_annotated_args
from ..utils.inspect_ import args_to_kwargs_by_sig

P = typing.ParamSpec("P")
R = typing.TypeVar("R")


def log_manager_handler(func: typing.Callable[P, R]) -> typing.Callable[P, R]:
    
    """Decorator for logging manager handler

    Features
    --------
    - Log enterance and parameters
    - Log exitance and return value
    - Use handler level logger to replace manager level logger

    Disabled Parameters
    ^^^^^^^^^^^^^^^^^^^
    Disabled parameters will not be logged.

    Use ``typing.Annotated[type, AnnotatedDirective.NOLOG]`` to
    mark the parameter as disabled.
    """
    func_name = func.__qualname__
    disabled_params = []

    # TODO get parameters annotated directive with xx
    param_sig = inspect.signature(func).parameters
    for param_name, param in param_sig.items():
        anno = param.annotation
        if is_annotated(anno):
            if get_annotated_args(anno)[0] == AD.NOLOG:
                disabled_params.append(param_name)

    @functools.wraps(func)
    def wrapper(
        *args: P.args, **kwargs: P.kwargs,
    ) -> R:
        
        self = args[0]
        if not isinstance(self, BaseManager):
            raise TypeError("First argument must be a BaseManager instance")

        to_log_parameters = kwargs.copy()
        if args:
            to_log_parameters.update(
                args_to_kwargs_by_sig(func, *args, offset=1)
            )
        if disabled_params:
            for param in disabled_params:
                to_log_parameters.pop(param, None)

        # bind logger
        logger = self._logger.bind(
            hanler_name=func_name,
        )
        self_copy = copy.copy(self)
        self_copy._logger = logger

        # enter log
        logger.info("Enter manager handler", paramters=to_log_parameters)
        
        # call
        new_args = list(args) 
        new_args[0] = self_copy
        result = func(*new_args, **kwargs)  # type: ignore

        # exit log
        logger.info("Exit manager handler", result=result)

        return result

    return wrapper
