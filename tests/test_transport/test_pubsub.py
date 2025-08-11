"""Tests of PubSub Transporter
"""

import asyncio
from unittest.mock import AsyncMock

from tests.test_dal.test_redis import TestRedisDAL
import pytest
from blue_firmament.task import Task, TaskID, TaskResult
from blue_firmament.transport.pubsub import PubSubTransporter


@pytest.fixture
async def redis_dal():
    """Provides a RedisDAL instance for testing and cleans up after."""
    dal = TestRedisDAL()
    yield dal
    # Clean up Redis after test
    await dal._client.flushdb()
    await dal._client.close()


@pytest.mark.asyncio
async def test_pubsub_transporter(redis_dal: TestRedisDAL):
    """
    Test that PubSubTransporter correctly receives a message and calls app.handle_task.
    """
    # 1. Setup
    app_mock = AsyncMock()
    app_mock.handle_task = AsyncMock()

    channel_name = "test_channel"
    transporter = PubSubTransporter(app_mock, redis_dal, channel_name)

    # 2. Run transporter in the background
    transporter_task = asyncio.create_task(transporter.start())
    await asyncio.sleep(0.1) # Give it a moment to subscribe

    # 3. Publish a message
    test_task = Task(
        task_id=TaskID(
            method="POST",
            path="/test/path",
        ),
        parameters={"param1": "value1"},
        metadata={"client_id": "1"}
    )
    await redis_dal.publish(await test_task.dump_to_bytes(), channel_name)

    # 4. Wait for message processing
    await asyncio.sleep(0.1)

    # 5. Assertions
    app_mock.handle_task.assert_called_once()
    call_args = app_mock.handle_task.call_args
    
    # Check the 'task' keyword argument
    called_task = call_args.kwargs['task']
    assert isinstance(called_task, Task)
    assert called_task.id == TaskID(method="POST", path="/test/path")
    assert called_task.parameters["param1"] == "value1"
    assert called_task.metadata.client_id == '1'

    # Check the 'task_result' keyword argument
    assert isinstance(call_args.kwargs['task_result'], TaskResult)

    # 6. Teardown
    await transporter.stop()
    transporter_task.cancel()
    try:
        await transporter_task
    except asyncio.CancelledError:
        pass # Expected on cancellation
