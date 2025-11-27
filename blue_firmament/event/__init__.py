"""Event module of BlueFirmament.

Event is the service unit of an BlueFirmament Application.

Design doc: :doc:`design/event`
"""

__all__ = [
    # Task-related exports (renamed from task module)
    'TaskID',
    'Task',
    'TaskStatus',
    'TaskMetadata',
    'TaskResult',
    'TaskHandler',
    'TaskRegistry',
    'TaskEntry',
    'listen_to',
    'Method',
    'LazyParameter',
    # Event-specific exports
    'set_event_broker',
    'Event',
    'emit',
    'simple_emit'
]

import typing
from typing import Optional as Opt

from .main import (
    TaskID, Task, TaskMetadata, Method, LazyParameter
)
from .result import (
    TaskStatus, TaskResult
)
from .handler import TaskHandler
from .registry import (
    TaskRegistry, TaskEntry, listen_to
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


class Event(Task):
    """Event is a specialized Task.
    """


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
        Fields must be defined in :meth:`blue_firmament.event.TaskMetadata`
    """
    event = Event(
        task_id=TaskID(method=None, path=name, separator='.'),
        parameters=parameters,
        metadata=metadata
    )
    return emit(event)
