"""BlueFirmament event system.
"""
import json
import typing

from . import Method
from .task import TaskID, TaskMetadata

if typing.TYPE_CHECKING:
    from .dal.base import QueueLikeDataAccessLayer


class EventEmitter:

    def __init__(
        self,
        queue_dal: QueueLikeDataAccessLayer,
        queue_name: str = "blue_firmament_event"  # Default queue name for events
    ):
        self.__queue_dal = queue_dal
        self.__queue_name = queue_name

    async def emit_task(
        self,
        method: Method,
        path: str,
        metadata: TaskMetadata,
        **parameters
    ) -> None:
        """Emit a task
        """
        task_id = TaskID(method=method, path=path)
        await self.__queue_dal.push(self.__queue_name, json.dumps({
            "task_id": str(task_id),
            "metadata": metadata.dump_to_dict(),
            "parameters": parameters
        }))
