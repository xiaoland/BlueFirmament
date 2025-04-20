

from .type import JsonDumpable
from ..scheme import BaseScheme
import datetime
import json


class JsonEncoder(json.JSONEncoder):
    
    def default(self, o):
        if isinstance(o, BaseScheme):
            return o.dump_to_dict()
        if isinstance(o, set):
            return list(o)
        if isinstance(o, datetime.datetime):
            return o.isoformat()

        return super().default(o)


def dumps_to_json(obj: JsonDumpable) -> str:
    
    """将对象序列化为JSON字符串
    """
    return json.dumps(obj, cls=JsonEncoder)
