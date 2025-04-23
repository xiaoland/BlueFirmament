'''Utils related to type checking and type hinting.'''

import typing
import types
import inspect

if typing.TYPE_CHECKING:
    from ..scheme import BaseScheme

def is_annotated(tp: typing.Type) -> typing.TypeGuard[typing.Annotated]:

    '''Check if the tp is typing.Annotated

    Example
    -------
    >>> is_annotated(typing.get_origin(typing.Annotated[str, ...]))
    True
    >>> is_annotated(typing.Annotated[str, ...])
    True
    '''
    if tp is not typing.Annotated:
        return typing.get_origin(tp) is typing.Annotated
    else:
        return True


@typing.overload
def get_origin(tp: types.UnionType) -> types.UnionType:
    ...
@typing.overload
def get_origin(tp: typing.Type) -> typing.Type:
    ...
def get_origin(tp: typing.Type | types.UnionType) -> typing.Type | types.UnionType:

    '''
    获取复杂类型的原始类型

    Behavior
    --------
    - typing.Annotated -> args[0]
    - typing.NewType -> __supertype__
    - typing.Union, types.UnionType 不会被处理，直接返回

    Example
    -------
    >>> get_origin(typing.Annotated[str, ...])
    str
    >>> get_origin(typing.NewType('MyStr', str))
    str
    >>> get_origin(typing.NewType('MyStr', typing.NewType('MyInt', int)))
    int
    >>> get_origin(typing.Union[str, int])
    typing.Union[str, int]
    >>> get_origin(str | int)
    str | int
    >>> get_origin(str)
    str
    '''
    if isinstance(tp, typing.NewType):
        tp_ = tp.__supertype__
        while isinstance(tp_, typing.NewType):
            tp_ = tp_.__supertype__
        return tp_
    
    res = typing.get_origin(tp) or tp

    if res is typing.Union or res is types.UnionType:
        return tp

    if res is typing.Annotated:
        return typing.get_args(tp)[0]
    
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

