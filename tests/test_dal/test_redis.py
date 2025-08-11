"""Tests of Redis DAL
"""
import asyncio
import pytest
import pytest_asyncio
from blue_firmament.dal.redis import RedisDAL
from blue_firmament.exceptions import NotFound

# 使用一个专用于测试的 Redis 数据库
TEST_DB = 15

class TestRedisDAL(
    RedisDAL,
    host="dev.hadream.local",
    port=6380,
    password="TwWm2iZrBqUb",
    db=TEST_DB
):
    pass

@pytest_asyncio.fixture
async def dal():
    """提供一个 TestRedisDAL 实例并在测试后清理数据库"""
    dal_instance = TestRedisDAL()
    # 确保连接成功
    await dal_instance._client.ping()
    yield dal_instance
    # 清理测试数据库
    await dal_instance._client.flushdb()
    await dal_instance._client.close()


@pytest.mark.asyncio
async def test_kv_operations(dal: TestRedisDAL):
    """测试 KV 存储的 get/set 操作"""
    key = "my-key"
    value = b"my-value"

    # 测试获取一个不存在的键
    assert await dal.get(key) is None

    # 测试设置和获取一个键值对
    await dal.set(key, value)
    assert await dal.get(key) == value


@pytest.mark.asyncio
async def test_queue_operations(dal: TestRedisDAL):
    """测试 Queue 的 push/pop 操作"""
    queue_name = "test-queue"
    dal.__queue_name__ = queue_name
    item = b"queue-item"

    # 测试从空队列中 pop (wait=False)
    with pytest.raises(NotFound):
        await dal.pop(wait=False)

    # 测试 push 和 pop
    await dal.push(item)
    popped_item = await dal.pop(wait=False)
    assert popped_item == item

@pytest.mark.asyncio
async def test_queue_blocking_pop(dal: TestRedisDAL):
    """测试 Queue 的阻塞 pop 操作"""
    queue_name = "test-queue-blocking"
    dal.__queue_name__ = queue_name
    item = b"blocking-item"

    async def pusher():
        # 等待一小段时间以确保 pop 已经开始阻塞
        await asyncio.sleep(0.1)
        await dal.push(item)

    # 同时运行 pop 和 pusher
    pop_task = asyncio.create_task(dal.pop(wait=True))
    push_task = asyncio.create_task(pusher())

    popped_item = await pop_task
    await push_task

    assert popped_item == item


@pytest.mark.asyncio
async def test_pubsub_operations(dal: TestRedisDAL):
    """测试 Pub/Sub 的 publish/listen 操作"""
    channel_name = "test-channel"
    dal.__channel_name__ = channel_name
    message_data = b"hello-world"

    await dal.subscribe()
    # 等待订阅生效
    await asyncio.sleep(0.01)

    # 在另一个任务中发布消息
    async def publisher():
        await dal.publish(message_data)

    listen_task = asyncio.create_task(dal.get_message())
    publisher_task = asyncio.create_task(publisher())

    message = await listen_task
    await publisher_task

    assert message["channel"] == channel_name.encode('utf-8')
    assert message["data"] == message_data

    await dal.unsubscribe(channel_name)

