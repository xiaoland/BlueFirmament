"""Tests of Event system.
"""

import asyncio
import pytest
from blue_firmament.event import set_event_broker, emit, simple_emit, Event
from blue_firmament.task import TaskID
from blue_firmament.dal.redis import RedisDAL


# TODO: use env variables or config file
class TestRedisDAL(
    RedisDAL,
    host="dev.hadream.local",
    port=6380,
    password="TwWm2iZrBqUb",
    db=0,
    channel_name='test_event_channel'
):
    pass


@pytest.fixture
async def event_broker():
    """Setup event broker and teardown."""
    broker = TestRedisDAL()
    await broker.subscribe()
    set_event_broker(broker)
    yield broker


async def listener(
    received_events: list,
    event_received: asyncio.Event,
    event_broker: TestRedisDAL
):
    async for message in event_broker.listen():
        received_events.append(Event.load_from_bytes(message["data"]))
        event_received.set()
        break

@pytest.mark.asyncio
async def test_emit(event_broker: TestRedisDAL):
    """Test emitting an event."""
    received_events = []
    event_received = asyncio.Event()

    listener_task = asyncio.create_task(listener(
        received_events,
        event_received,
        event_broker
    ))

    event_to_emit = Event(
        task_id=TaskID(method=None, path="test.event", separator='.'),
        parameters={"foo": "bar"}
    )
    await emit(event_to_emit)

    await asyncio.wait_for(event_received.wait(), timeout=1.0)
    listener_task.cancel()

    assert len(received_events) == 1
    assert received_events[0].id.path == event_to_emit.id.path
    assert received_events[0].parameters["foo"] == "bar"


@pytest.mark.asyncio
async def test_simple_emit(event_broker: TestRedisDAL):
    """Test simple_emit function."""
    received_events = []
    event_received = asyncio.Event()

    listener_task = asyncio.create_task(listener(
        received_events,
        event_received,
        event_broker
    ))

    event_name = "user.created"
    event_params = {"user_id": 123}
    await simple_emit(name=event_name, parameters=event_params)

    await asyncio.wait_for(event_received.wait(), timeout=1.0)
    listener_task.cancel()

    assert len(received_events) == 1
    assert received_events[0].id.path == event_name.replace('.', '/')
    assert received_events[0].parameters["user_id"] == 123
