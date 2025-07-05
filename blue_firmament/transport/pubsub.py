"""Transporter listening to a Pub/Sub model channel.
"""

__all__ = [
    "PubSubTransporter"
]

import json
import typing
from typing import Annotated as Anno, Optional as Opt, Literal as Lit
from ..transport.base import BaseTransporter
from ..task import Task, TaskResult
from ..dal.base import PubSubLikeDataAccessLayer, PubSubMessage

if typing.TYPE_CHECKING:
    from ..core import BlueFirmamentApp


class PubSubTransporter(BaseTransporter):

    def __init__(
        self,
        app: "BlueFirmamentApp",
        pubsub_dal: PubSubLikeDataAccessLayer,
        *channel_names: str,
        name: str = "default"
    ):
        """
        :param pubsub_dal: A PubSubDAL not subscribed to any channel.
        """
        super().__init__(app=app, name=name)

        self.__stop = False
        self.__pubsub_dal = pubsub_dal
        self.__channel_names = channel_names

    async def start(self):
        self.__stop = False
        await self.__pubsub_dal.subscribe(*self.__channel_names)
        while not self.__stop:
            message = await self.__pubsub_dal.get_message()
            await self(message)

    async def stop(self):
        self.__stop = True
        await self.__pubsub_dal.unsubscribe(*self.__channel_names)

    async def __call__(self, message: PubSubMessage):
        await self._app.handle_task(
            task=Task.load_from_bytes(message["data"]),
            task_result=TaskResult(),
            transporter=self
        )

