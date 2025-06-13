import json
import multiprocessing
import asyncio
from blue_firmament import BlueFirmamentApp
from blue_firmament.task import Task
from blue_firmament.transport.redis_pubsub import RedisPubSubTransporter
from blue_firmament.transport.redis_pubsub import RedisConfig
import redis.asyncio as aioredis
import redis


app = BlueFirmamentApp()


def publish_test_message():
    r2 = redis.Redis(host="192.168.3.158", port=6380, password="TwWm2iZrBqUb")
    r2.publish(
        "blue_firmament_redis_pubsub",
        json.dumps({
            "method": "GET",
            "path": "/test",
        })
    )


def start_listening(modified_app: BlueFirmamentApp):
    r = aioredis.Redis(host="192.168.3.158", port=6380, password="TwWm2iZrBqUb")
    t = RedisPubSubTransporter(
        app=modified_app,
        **RedisConfig(redis=r)
    )
    asyncio.run(t.start_listening())

async def app_handle_task_mock(task: Task, task_result):
    print(task.id)

async def test_start_listening(monkeypatch):
    """"""
    monkeypatch.setattr(app, "handle_task", app_handle_task_mock)

    p2 = multiprocessing.Process(target=start_listening, args=(app,))
    p1 = multiprocessing.Process(target=publish_test_message)
    p2.start()
    p1.start()
    p2.join()
    p1.join()
