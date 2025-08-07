"""Utils enhancing inspect module"""

__all__ = [
    'is_instance_method_by_signature',
    'has_kwarg_by_sig',
    'args_to_kwargs_by_sig',
    'get_param_types',
]

import inspect
import typing


def is_instance_method_by_signature(
    func: typing.Callable
) -> bool:
    """Check if the function is an instance method by checking its signature.

    If the function has a 'self' parameter and positioned as the first parameter,
    it is considered an instance method.
    """

    sig = inspect.signature(func)
    params = sig.parameters
    if len(params) > 0:
        first_param = tuple(params.values())[0]
        if first_param.name == 'self':
            return True
    return False


def has_kwarg_by_sig(
    func: typing.Callable, kwarg_name: str
) -> bool:
    """Check if the function has a specific keyword argument by checking its signature.

    :param func: The function to check
    :param kwarg_name: The name of the keyword argument to check for
    """
    sig = inspect.signature(func)
    params = sig.parameters
    return any(
        param.name == kwarg_name and param.kind in (
            inspect.Parameter.KEYWORD_ONLY, inspect.Parameter.VAR_KEYWORD
        )
        for param in params.values()
    )


def args_to_kwargs_by_sig(
    func: typing.Callable, *args,
    offset: int = 0,
    try_default: bool = True,
) -> typing.Dict[str, typing.Any]:
    """Convert positional arguments to keyword arguments based on the function's signature.

    :param func: The function to check
    :param args: The positional arguments to convert
    :param offset: The number of positional arguments to skip (on sig arguments)
    :param try_default: If True, use default values for missing positional arguments
    """
    sig = inspect.signature(func)
    params = sig.parameters
    kwargs = {}

    for i, (name, param) in enumerate(params.items()):
        if i < offset:
            continue
        if i < len(args):
            kwargs[name] = args[i-offset]
        else:
            if try_default:
                if param.default is not param.empty:
                    kwargs[name] = param.default

    return kwargs

def get_param_types(
    func: typing.Callable
) -> typing.Mapping[str, type]:
    """Get the parameter types of a function based on its signature.

    :param func: The function to inspect
    :return: A dictionary mapping parameter names to their types
    """
    sig = inspect.signature(func)
    return {
        name: (
            param.annotation
            if param.annotation is not inspect.Parameter.empty
            else typing.Any
        )
        for name, param in sig.parameters.items()
    }

