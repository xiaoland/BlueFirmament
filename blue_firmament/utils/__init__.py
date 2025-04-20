
import threading
import typing
import enum
import asyncio
import inspect

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
def dump_enum(enum_member: enum.Enum | DumpEnumValueType) -> DumpEnumValueType:

    '''序列化可能为枚举的对象为目标类型'''

    if isinstance(enum_member, enum.Enum):
        return enum_member.value
    return enum_member

EnumType = typing.TypeVar('EnumType', bound=enum.Enum)
def load_enum(
    enum_class: typing.Type[EnumType], 
    name: str | int | EnumType,
) -> EnumType:

    '''获取枚举类中对应值的成员'''
    if isinstance(name, enum.Enum):
        return name
    else:
        try:
            return enum_class(name)
        except ValueError as e:
            raise ValueError(
                f"Value '{name}' is not a valid member of enum '{enum_class.__name__}'"
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


async def call_function_as_async(
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
    # process func is a instance with __call__ method
    if hasattr(func, '__call__') and not (
        inspect.isfunction(func) or inspect.ismethod(func)
    ):
        func = func.__call__  # type: ignore[assignment]

    if inspect.iscoroutinefunction(func):
        # Function is async, run it with asyncio
        return await func(*args, **kwargs)
    else:
        # Function is synchronous, call it directly
        return func(*args, **kwargs)


def get_optional(value: T | None, default: T) -> T:
    
    """
    Returns the value if it is not None, otherwise returns the default value.
    
    :param value: The value to check
    :param default: The default value to return if value is None
    """
    return value if value is not None else default
