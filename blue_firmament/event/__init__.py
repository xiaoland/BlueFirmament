"""Event module of BlueFirmament.

Event is the service unit of an BlueFirmament Application.

Design doc: :doc:`design/event`
"""

__all__ = [
    'EventID',
    'Event',
    'EventStatus',
    'EventMetadata',
    'EventResult',
    'EventHandler',
    'EventBus',
    'EventRegistry',  # backward compatibility alias
    'EventEntry',
    'listen_to',
    'Method',
    'LazyParameter',
    'set_event_broker',
    'emit',
    'simple_emit',
    'BaseMiddleware',
    'MiddlewaresT',
    'NextT',
]

import typing
from typing import Optional as Opt

from .main import (
    EventID, Event, EventMetadata, Method, LazyParameter
)
from .result import (
    EventStatus, EventResult
)
from .handler import EventHandler
from .registry import (
    EventBus, EventRegistry, EventEntry, listen_to
)
from .middleware import (
    BaseMiddleware, MiddlewaresT, NextT
)
from ..log import get_logger
from ..dal.base import PubSubLikeDataAccessLayer

LOGGER = get_logger(__name__)


EVENT_BROKER: PubSubLikeDataAccessLayer
"""A PubSubDAL.

- must configured a default channel. 
"""

def set_event_broker(event_broker: PubSubLikeDataAccessLayer):
    global EVENT_BROKER
    if not isinstance(event_broker, PubSubLikeDataAccessLayer):
        raise TypeError("event_broker must be a PubSubLikeDataAccessLayer instance")
    EVENT_BROKER = event_broker


async def emit(event: Event) -> None:
    """Emit an event to the event broker.
    """
    await EVENT_BROKER.publish(await event.dump_to_bytes())
    LOGGER.info("Event emitted", event_id=event.id)

def simple_emit(
    name: str,
    parameters: Opt[dict] = None,
    metadata: Opt[dict] = None,
) -> typing.Coroutine[None, None, None]:
    """Emit an event in a simple way.

    :param name: Name of the event.
        e.g. "user.created", "order.completed"
    :param parameters: Parameters of the event.
    :param metadata: Metadata of the event.
        Fields must be defined in :meth:`blue_firmament.event.EventMetadata`
    """
    event = Event(
        event_id=EventID(method=None, path=name, separator='.'),
        parameters=parameters,
        metadata=metadata
    )
    return emit(event)
