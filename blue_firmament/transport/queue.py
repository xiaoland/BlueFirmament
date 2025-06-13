"""Queue based transporter.
"""
import json
import typing
from .base import BaseTransporter
from ..task import Task, TaskMetadata, TaskResult

if typing.TYPE_CHECKING:
    from ..dal.base import QueueLikeDataAccessLayer
    from .. import BlueFirmamentApp


class QueueTransporter(BaseTransporter):

    def __init__(
        self,
        app: BlueFirmamentApp,
        queue_dal: QueueLikeDataAccessLayer,
        queue_name: str = "blue_firmament_event",
        handling_queue_name: str = "blue_firmament_handling_event"
    ):
        super().__init__(app)
        self.__dal = queue_dal
        self.__queue_name = queue_name
        self.__handling_queue_name = handling_queue_name
        self.__stop = False

    async def start_listening(self):
        while not self.__stop:
            event = await self.__dal.blocking_pop_and_push(
                queue=self.__queue_name, dst_queue=self.__handling_queue_name
            )
            await self(event)

    async def stop_listening(self):
        self.__stop = True

    async def __call__(self, event: bytes):
        parsed_event = json.loads(event)
        if isinstance(parsed_event, dict):
            task_id = parsed_event["task_id"]
            metadata = parsed_event.get("metadata", {})
            parameters = parsed_event.get("parameters", {})

            await self._app.handle_task(
                task=Task(
                    task_id=task_id,
                    metadata=TaskMetadata(**metadata),
                    parameters=parameters
                ),
                task_result=TaskResult()
            )
        else:
            self._logger.warning(f"Unsupported event type: {type(parsed_event)}")
