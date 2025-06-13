import json
import typing
from typing import Annotated as Anno, Optional as Opt, Literal as Lit
import redis.asyncio as redis
from blue_firmament.transport.base import BaseTransporter
from blue_firmament.task import Task, TaskID, TaskResult

if typing.TYPE_CHECKING:
    from blue_firmament.core import BlueFirmamentApp


class RedisConfig(typing.TypedDict):
    host: typing.NotRequired[str]
    port: typing.NotRequired[int]
    db: typing.NotRequired[int]
    password: typing.NotRequired[str]
    redis: typing.NotRequired[redis.Redis]


class RedisPubSubTransporter(BaseTransporter):

    def __init__(
        self,
        app: "BlueFirmamentApp",
        channel: str = "blue_firmament_redis_pubsub",
        **redis_config: RedisConfig
    ):
        super().__init__(app)

        _redis = redis_config.get("redis")
        if _redis is None:
            _redis = redis.Redis(
                host=redis_config.get("host", ""),
                port=redis_config.get("port", 0),
                db=redis_config.get("db", 0),
                password=redis_config.get("password")
            )
        else:
            _redis = redis_config.get("redis", None)
            if _redis is None:
                raise ValueError("redis or (host, port) are required")

        self.__redis_pubsub = _redis.pubsub()
        self.__channel = channel
        self.__stop = False

    async def start_listening(self):
        self.__stop = False
        await self.__redis_pubsub.subscribe(self.__channel)
        while not self.__stop:
            message = await self.__redis_pubsub.get_message(ignore_subscribe_messages=True)
            if message is not None:
                await self(message)

    async def stop_listening(self):
        self.__stop = True

    async def __call__(self, message: dict):
        if message['type'] == 'message':
            data = json.loads(message['data'])

            method = data.get("method", None)
            path = data.get("path", "")
            task_id = TaskID(method, path=path)

            parameters = data.get("parameters", {})
            metadata = data.get("metadata", {})

            await self._app.handle_task(
                task=Task(
                    task_id=task_id,
                    parameters=parameters,
                    metadata=self._parse_task_metadata(metadata),
                ),
                task_result=TaskResult()
            )
        self._logger.warning(f"Received unknown message type: {message['type']}")

