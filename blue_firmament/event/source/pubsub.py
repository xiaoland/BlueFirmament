"""Event source listening to a Pub/Sub model channel.

TODO better logging
"""

__all__ = [
    "PubSubEventSource",
    "PubSubEventSource"  # backward compatibility
]

import typing

from ...exceptions import EventHandlerNotFound
from .base import BaseEventSource
from .. import Event, EventResult
from ...dal.base import PubSubLikeDataAccessLayer, PubSubMessage

if typing.TYPE_CHECKING:
    from ...core import BlueFirmamentApp


class PubSubEventSource(BaseEventSource):

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
        self._logger.info("Listening to Pub/Sub channels", channels=self.__channel_names)
        async for message in self.__pubsub_dal.listen():
            try:
                await self(message)
            except EventHandlerNotFound as e:
                self._logger.warning("No handler found for the task", task=e.task_id)
            except Exception as e:
                self._logger.exception(
                    f"Unknown error occured when handling event from Pub/Sub {self.name}"
                )
            if self.__stop:
                break

    async def stop(self):
        self.__stop = True
        await self.__pubsub_dal.unsubscribe(*self.__channel_names)
        self._logger.info("Stop listening to Pub/Sub channels", channels=self.__channel_names)

    async def __call__(self, message: PubSubMessage):
        await self._app.handle_task(
            task=Event.load_from_bytes(message["data"]),
            task_result=EventResult(),
            event_source=self
        )


# Backward compatibility alias
PubSubEventSource = PubSubEventSource

