"""Event source listening to a Pub/Sub model channel.

TODO better logging
"""

__all__ = [
    "PubSubEventSource",
]

import typing

from ...exceptions import EventHandlerNotFound
from .base import BaseEventSource
from .. import Event, EventResult
from ...dal.base import PubSubLikeDataAccessLayer, PubSubMessage

if typing.TYPE_CHECKING:
    from ..bus import EventBus


class PubSubEventSource(BaseEventSource):

    def __init__(
        self,
        event_bus: "EventBus",
        pubsub_dal: PubSubLikeDataAccessLayer,
        *channel_names: str,
        name: str = "default"
    ):
        """
        :param event_bus: The event bus to dispatch events to
        :param pubsub_dal: A PubSubDAL not subscribed to any channel.
        :param channel_names: Names of channels to subscribe to
        :param name: Name identifier for this event source
        """
        super().__init__(event_bus=event_bus, name=name)

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
                self._logger.warning("No handler found for the event", event_id=e.event_id)
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
        await self._event_bus.emit(
            event=Event.load_from_bytes(message["data"]),
            event_result=EventResult(),
        )

