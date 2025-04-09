
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

def get_enum_member(
    enum_class: typing.Type[enum.Enum], name: str | int,
    fallback_value: DumpEnumValueType
) -> DumpEnumValueType:

    '''获取枚举类中对应值的成员'''
    try:
        return enum_class(name)
    except AttributeError:
        return fallback_value

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
    return getter(value) if value else fallback


def call_function(func: typing.Callable, *args, **kwargs) -> typing.Any:

    """
    Calls the given function with the provided arguments, handling both
    synchronous and asynchronous functions transparently.
    
    This allows calling async functions from synchronous code without using
    the async/await syntax.
    
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
        result1 = call_function(sync_func, 5)  # Returns 10
        result2 = call_function(async_func, 5)  # Returns 15
    ```
    """
    if inspect.iscoroutinefunction(func):
        # Function is async, run it with asyncio
        return asyncio.get_event_loop().run_until_complete(func(*args, **kwargs))
    else:
        # Function is synchronous, call it directly
        return func(*args, **kwargs)
