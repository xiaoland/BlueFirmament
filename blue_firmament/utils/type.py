'''Utils related to type checking and type hinting.'''

import typing
import inspect
from ..scheme import BaseScheme

def is_annotated(val: typing.Any) -> typing.TypeGuard[typing.Annotated]:
    '''Check if the value is typing.Annotated

    :param val: The value to check.
    :return: True if the value is annotated, False otherwise.

    Imple
    -----
    Check if the value has the `__origin__` and `__metadata__` attributes,
    '''
    return hasattr(val, '__origin__') and hasattr(val, '__metadata__')

def get_origin(type: typing.Type) -> typing.Type:

    '''
    兼容typing.Annotated和typing.NewType的get_origin方法
    '''
    
    if getattr(type, '__class__') == typing.NewType:
        type = type.__supertype__
    
    res = typing.get_origin(type) or type

    if res == typing.Annotated:
        return typing.cast(typing.Type, type.__origin__)
    
    return res


T = typing.TypeVar('T', bound=typing.Type)
def ismethodorigin(func, origin: T) -> typing.TypeGuard[T]:
    
    '''判断是否为某个类的方法

    包括实例方法、类方法：
    
    ```python
    class A:
        def method(self):
            pass
        @classmethod
        def cls_method(cls):
            pass
    
    A.method # no
    A.cls_method # yes
    a = A()
    a.method # yes
    ```

    :param param: 要检查的参数
    :param origin: 要检查的类
    '''

    if inspect.ismethod(func):
        return isinstance(func.__self__, origin)
    elif isclassmethod(func):
         return func.__self__ is origin
    
    return False

def isclassmethod(func: typing.Any) -> bool:

    '''Check if the function is a classmethod
    '''
    return inspect.ismethod(func) and hasattr(func, '__self__') and func.__self__ is not None


JsonDumpable = typing.Union[
    str, int, float, bool, None, 
    typing.List['JsonDumpable'], 
    typing.Tuple['JsonDumpable', ...],
    typing.Dict[str, 'JsonDumpable'],
    BaseScheme
]
'''可以序列化为JSON的类型

其中BaseScheme实际上不能被json.dumps处理，需要通过我们自定义的json_dumps来处理
'''
