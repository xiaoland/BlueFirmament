

from .type import JsonDumpable
from ..scheme import BaseScheme

import json

def dumps_to_json(obj: JsonDumpable) -> str:
    
    """将对象序列化为JSON字符串
    
    """

    if isinstance(obj, BaseScheme):
        to_dump = obj.dump_to_dict()
    else:
        to_dump = obj
    
    return json.dumps(to_dump)
