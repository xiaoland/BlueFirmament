'''Utils related to type checking and type hinting.'''

import typing

def is_annotated(val: typing.Any) -> typing.TypeGuard[typing.Annotated]:
    '''Check if the value is typing.Annotated

    :param val: The value to check.
    :return: True if the value is annotated, False otherwise.

    Imple
    -----
    Check if the value has the `__origin__` and `__metadata__` attributes,
    '''
    return hasattr(val, '__origin__') and hasattr(val, '__metadata__')

def get_origin(type: typing.Any) -> typing.Type:
    return typing.get_origin(type) or type


JsonDumpable = typing.Union[
    str, int, float, bool, None, 
    typing.List['JsonDumpable'], 
    typing.Tuple['JsonDumpable', ...],
    typing.Dict[str, 'JsonDumpable'],
]
