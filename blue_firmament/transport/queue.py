"""Transporter listening to a Queue.
"""
import typing
from .base import BaseTransporter
from ..task import Task, TaskResult

if typing.TYPE_CHECKING:
    from ..dal.base import QueueLikeDataAccessLayer
    from .. import BlueFirmamentApp


class QueueTransporter(BaseTransporter):
    """

    :ivar __dal: Listening this queue dal for tasks.
    :ivar __handling_dal: The queue storing handling tasks.
    """

    def __init__(
        self,
        app: BlueFirmamentApp,
        queue_dal: QueueLikeDataAccessLayer,
        handling_queue_dal: QueueLikeDataAccessLayer
    ):
        super().__init__(app)
        self.__dal = queue_dal
        self.__handling_dal = handling_queue_dal
        self.__stop = False

    async def start(self):
        while not self.__stop:
            await self(await self.__dal.pop())

    async def stop(self):
        self.__stop = True

    async def __call__(self, raw: bytes):
        await self._app.handle_task(
            task=Task.load_from_bytes(raw),
            task_result=TaskResult()
        )
