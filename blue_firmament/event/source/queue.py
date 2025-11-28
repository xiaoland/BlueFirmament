"""Event source listening to a Queue.
"""
import typing
from .base import BaseEventSource
from .. import Event, EventResult

if typing.TYPE_CHECKING:
    from ...dal.base import QueueLikeDataAccessLayer
    from ..bus import EventBus


class QueueEventSource(BaseEventSource):
    """Event source that listens to a queue for events.

    :ivar __dal: Listening this queue dal for events.
    :ivar __handling_dal: The queue storing handling events.
    """

    def __init__(
        self,
        event_bus: "EventBus",
        queue_dal: "QueueLikeDataAccessLayer",
        handling_queue_dal: "QueueLikeDataAccessLayer",
        name: str = "default"
    ):
        """
        :param event_bus: The event bus to dispatch events to
        :param queue_dal: The queue to listen for events
        :param handling_queue_dal: The queue to store events being handled
        :param name: Name identifier for this event source
        """
        super().__init__(event_bus=event_bus, name=name)
        self.__dal = queue_dal
        self.__handling_dal = handling_queue_dal
        self.__stop = False

    async def start(self):
        while not self.__stop:
            await self(await self.__dal.pop())

    async def stop(self):
        self.__stop = True

    async def __call__(self, raw: bytes):
        await self._event_bus.emit(
            event=Event.load_from_bytes(raw),
            event_result=EventResult(),
        )
