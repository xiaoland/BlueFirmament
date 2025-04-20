'''Utils related to type checking and type hinting.'''

import typing
import types
import inspect

if typing.TYPE_CHECKING:
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
    typing.Set['JsonDumpable'],
    "BaseScheme"
]
'''可以序列化为JSON的类型

其中BaseScheme实际上不能被json.dumps处理， \n
需要通过我们自定义的json_dumps来处理，调用 :func:`utils.json.dumps_to_json`
'''
def is_json_dumpable(val: typing.Any) -> typing.TypeGuard[JsonDumpable]:

    """

    TODO
    ----
    - 对于容器类型，没有进一步对元素判断
    """
    if val is None:
        return True

    from ..scheme import BaseScheme
    if isinstance(val, (
        str, int, float, bool,
        list, tuple, dict, set,
        BaseScheme
    )):
        return True
    
    return False

def is_union_type(tp):
  """Checks if a type hint is a union type (typing.Union or |)."""
  origin = typing.get_origin(tp)
  return origin is typing.Union or origin is types.UnionType


def add_type_to_namespace(type_: typing.Type, namespace: dict):

    '''将类型添加到命名空间

    :param type: 要添加的类型
    :param namespace: 命名空间
    '''
    try:
        namespace[type_.__name__] = type_
    except AttributeError:
        raise ValueError('Cannnot process this type %s' % type_)


def is_mutable(value: typing.Any) -> bool:
    
    '''判断一个值是否为可变对象

    :param value: 要判断的值
    '''
    if isinstance(value, (list, dict, set)):
        return True
    elif hasattr(value, '__hash__'):
        return False  # not strict enough
    elif hasattr(value, '__dict__'):
        return True  # need verification
    else:
        return False


def safe_issubclass(
    obj: typing.Any, classinfo: T
) -> typing.TypeGuard[T]:
    
    return isinstance(obj, type) and issubclass(obj, classinfo)

