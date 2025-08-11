
__all__ = [
    'singleton',
    'call_as_async',
    'call_as_sync',
    'dump_iterable',
    'try_convert_str',
]

import asyncio
import inspect
import threading
import typing
import nest_asyncio

T = typing.TypeVar('T')


def singleton(cls):

    """
    A decorator to implement a global single instance for a class.
    This decorator uses a lock to ensure thread-safe instantiation.
    """
    _instances = {}  # Store instances of decorated classes
    _lock = threading.Lock()

    def get_instance(*args, **kwargs):
        """
        Retrieves or creates the singleton instance.
        """
        with _lock:  # Ensure thread-safe instantiation
            if cls not in _instances:
                _instances[cls] = cls(*args, **kwargs)

        return _instances[cls]

    return get_instance


async def call_as_async(
    func: typing.Callable, *args, **kwargs
) -> typing.Any:
    """Call both sync and async function asynchronously.

    :param func: The async/sync function to call
    :param args: Positional arguments to pass to the function
    :param kwargs: Keyword arguments to pass to the function

    Returns
    --------
    The result of the function call

    Example
    --------
    ```python
        def sync_func(x):
            return x * 2

        async def async_func(x):
            await asyncio.sleep(0.1)
            return x * 3

        # Both can be called the same way
        result1 = await call_function_as_async(sync_func, 5)  # Returns 10
        result2 = await call_function_as_async(async_func, 5)  # Returns 15
    ```
    """
    call = getattr(func, "__call__", None)

    if (
        call is not None and inspect.iscoroutinefunction(call)
        or
        inspect.iscoroutinefunction(func)
    ):
        # Function is async, run it with await
        return await func(*args, **kwargs)
    else:
        # Function is synchronous, call it directly
        return func(*args, **kwargs)


def call_as_sync(func: typing.Callable, *args, **kwargs) -> typing.Any:
    """Call both sync and async function synchronously.
    """
    res = func(*args, **kwargs)
    if isinstance(res, typing.Coroutine):
        nest_asyncio.apply()
        return asyncio.run(res)
    return res


IterT = typing.TypeVar('IterT', bound=typing.Iterable)
def dump_iterable(seq_cls: type[IterT], value: typing.Any) -> IterT:
    if isinstance(value, seq_cls):
        return value
    else:
        return seq_cls(value)


def try_convert_str(value: str) -> typing.Union[str, int, float, bool, None]:
    """
    Attempts to convert a string value to a Python primitive type.
    """
    if value.isdigit():
        return int(value)
    try:
        return float(value)
    except ValueError:
        pass
    if value.lower() == 'true':
        return True
    elif value.lower() == 'false':
        return False
    if value.lower() == 'null' or value == '':
        return None
    return value
