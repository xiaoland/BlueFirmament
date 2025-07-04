
import threading
import typing
import enum
import time
import asyncio
import nest_asyncio
import inspect


# TODO don't put anything in `__init__.py``

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


DumpEnumValueType = typing.TypeVar('DumpEnumValueType')
@typing.overload
def dump_enum(enum_member: enum.Enum) -> DumpEnumValueType:
    ...
@typing.overload
def dump_enum(enum_member: DumpEnumValueType) -> DumpEnumValueType:
    ...
@typing.overload
def dump_enum(enum_member: None) -> None:
    ...
def dump_enum(enum_member: enum.Enum | DumpEnumValueType | None) -> DumpEnumValueType | None:
    """Dump enum member to its value.
    """
    if enum_member is None:
        return None
    if isinstance(enum_member, enum.Enum):
        return enum_member.value
    return enum_member

EnumType = typing.TypeVar('EnumType', bound=enum.Enum)
@typing.overload
def load_enum(
    enum_class: typing.Type[EnumType],
    name: str | int | EnumType,
) -> EnumType:
    ...
@typing.overload
def load_enum(
    enum_class: typing.Type[EnumType],
    name: None,
) -> None:
    ...
def load_enum(
    enum_class: typing.Type[EnumType], 
    value: str | int | EnumType | None,
) -> EnumType | None:
    """Resolve enum member from value.

    :param enum_class: The enum class.
    :param value: The enum member value or a member of the enum class.

    :raise ValueError: If no enum member for this value in the enum class.
    :returns: Enum member. If you pass None as name, returns None.
    """
    if value is None:
        return None
    if isinstance(value, enum.Enum):
        return value
    else:
        try:
            return enum_class(value)
        except ValueError as e:
            raise ValueError(
                f"Value '{value}' is not a valid member of enum '{enum_class.__name__}'"
            ) from e

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


GetterReturnType = typing.TypeVar('GetterReturnType')
FallbackType = typing.TypeVar('FallbackType')
def get_when_truly(
    value: T, getter: typing.Callable[[T], GetterReturnType] = lambda x: x, fallback: FallbackType = None
) -> GetterReturnType | FallbackType:
    
    """
    TODO
    ----
    - merge with get_optional
    """

    return getter(value) if value else fallback


def unwrap_callable(callbale: typing.Callable):

    # process func is a instance with __call__ method
    if hasattr(callbale, '__call__') and not (
        inspect.isfunction(callbale) or inspect.ismethod(callbale)
    ):
        return callable.__call__  # type: ignore[assignment]
    
    return callable

async def call_as_async(
    func: typing.Callable, *args, **kwargs
) -> typing.Any:

    """
    Calls the given function with the provided arguments, handling both
    synchronous and asynchronous functions transparently.
    
    This reduce the need to check if the function is async or sync before calling it. (treat it as async)
    
    :param func: The async/sync function to call
    :param *args: Positional arguments to pass to the function
    :param **kwargs: Keyword arguments to pass to the function
        
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
    func = unwrap_callable(func)

    if inspect.iscoroutinefunction(func):
        # Function is async, run it with await
        return await func(*args, **kwargs)
    else:
        # Function is synchronous, call it directly
        return func(*args, **kwargs)
    
def call_function(func: typing.Callable, *args, **kwargs) -> typing.Any:

    """Call both sync and async function.
    """

    res = func(*args, **kwargs)
    if isinstance(res, typing.Coroutine):
        nest_asyncio.apply()
        return asyncio.run(res)
    return res

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

def get_optional(value: T | None, default: T) -> T:
    
    """
    Returns the value if it is not None, otherwise returns the default value.
    
    :param value: The value to check
    :param default: The default value to return if value is None
    """
    return value if value is not None else default


def retry(
    max: int = 1,
    default_delay: int | float = 0.1,
):

    """A decorator retring function when it raises an exception.

    :param max: The maximum number of retries
    :param default_delay: The delay between retries in seconds
    """
    from ..exceptions import Retryable
    def decorator(func: typing.Callable):
        def wrapper(*args, **kwargs):
            for attempt in range(max):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if isinstance(e, Retryable):
                        delay = e.delay
                    else:
                        delay = default_delay
                    
                    if attempt < max - 1:
                        time.sleep(delay * 1000)
                    else:
                        raise e
        return wrapper
    return decorator
