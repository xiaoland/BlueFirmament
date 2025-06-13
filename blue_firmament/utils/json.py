

import typing
import enum
import datetime
import json
from ..scheme.field import FieldValueProxy
from .type import JsonDumpable
from ..scheme import BaseScheme
from ..log import get_logger
from ..task.result import JsonBody

logger = get_logger(__name__)


class JsonEncoder(json.JSONEncoder):
    
    def default(self, o):
        if isinstance(o, BaseScheme):
            return o.dump_to_dict()
        if isinstance(o, JsonBody):
            return o.dump_to_dict()
        if isinstance(o, FieldValueProxy):
            return o.obj
        if isinstance(o, set):
            return list(o)
        if isinstance(o, datetime.datetime):
            return o.isoformat()
        if isinstance(o, enum.Enum):
            return o.value

        return super().default(o)


def override_json_encoder(cls: typing.Optional[json.JSONEncoder] = None):
    logger.info("Json lib's encoder has been overriden")
    json.JSONEncoder = cls or JsonEncoder
override_json_encoder()

def dumps_to_json(obj: JsonDumpable) -> str:
    
    """将对象序列化为JSON字符串
    """
    return json.dumps(obj, cls=JsonEncoder)
