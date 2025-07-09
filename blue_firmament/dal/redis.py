
import typing
from typing import Annotated as Anno, Optional as Opt, Literal as Lit
import redis.asyncio as redis
from .base import KVLikeDataAccessLayer, QueueLikeDataAccessLayer, PubSubLikeDataAccessLayer, PubSubMessage
from .types import StrictDALPath
from ..data.settings.dal import get_setting as get_dal_setting
from ..exceptions import NotFound


class RedisDAL(
    KVLikeDataAccessLayer,
    QueueLikeDataAccessLayer,
    PubSubLikeDataAccessLayer
):

    def __init_subclass__(
        cls,
        host: str = "localhost",
        port: int = 6379,
        password: Opt[str] = None,
        db: int = 0,
        **kwargs
    ):
        cls.__host = host
        cls.__port = port
        cls.__password = password

        return super().__init_subclass__(
            default_path=StrictDALPath((db,)),
            **kwargs
        )

    def __init__(self) -> None:
        self._client = redis.Redis(
            host=self.__host,
            port=self.__port,
            password=self.__password,
            db=self.default_path[0]
        )
        self._pubsub = self._client.pubsub(ignore_subscribe_messages=True)

    def get(self, key: str) -> Opt[typing.Any]:
        return self._client.get(key)

    async def set(self, key: str, value: typing.Any) -> None:
        await self._client.set(key, value)

    async def push(self, item: bytes) -> None:
        await self._client.lpush(self.__queue_name__, item)

    async def pop(self, wait: bool = True) -> bytes:
        if not wait:
            res = await self._client.lpop(self.__queue_name__)
        else:
            res = await self._client.blpop(*self.__queue_name__, timeout=0)

        if res is None:
            raise NotFound(f"No available items in queue {self.__queue_name__}")
        if isinstance(res, list):
            res = res[0]
        if isinstance(res, str):
            return res.encode('utf-8')

        return res

    async def publish(self, item: bytes, *channel_names: str) -> None:
        if not channel_names:
            channel_names = (self.__channel_name__,)
        for channel_name in channel_names:
            await self._client.publish(channel_name, item)

    async def subscribe(self, *channel_names: str) -> None:
        if not channel_names:
            channel_names = (self.__channel_name__,)
        await self._pubsub.subscribe(*channel_names)

    async def unsubscribe(self, *channel_names: str) -> None:
        if not channel_names:
            channel_names = (self.__channel_name__,)
        await self._pubsub.unsubscribe(*channel_names)
        await self._pubsub.close()

    async def get_message(self, timeout: int = 0) -> PubSubMessage:
        message = None
        while message is None:
            message = await self._pubsub.get_message(timeout=timeout)

        return PubSubMessage(
            channel=message["channel"],
            data=message["data"],
        )


class DefaultRedisDAL(
    RedisDAL,
    host=get_dal_setting().redis_host,
    port=get_dal_setting().redis_port,
    password=get_dal_setting().redis_password,
    db=get_dal_setting().redis_db
):
    pass
