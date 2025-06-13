
import typing
from typing import Annotated as Anno, Optional as Opt, Literal as Lit
import redis.asyncio as redis
from .base import KVLikeDataAccessLayer, QueueLikeDataAccessLayer
from .types import StrictDALPath
from .._types import Undefined
from ..auth import AuthSession


class RedisDAL(KVLikeDataAccessLayer, QueueLikeDataAccessLayer):

    def __init_subclass__(
        cls,
        host: str = "localhost",
        port: int = 6379,
        password: Opt[str] = None,
        db: int = 0
    ):
        cls.__host = host
        cls.__port = port
        cls.__password = password

        return super().__init_subclass__(
            default_path=StrictDALPath(())
        )

    def __init__(self, session: AuthSession) -> None:
        super().__init__(session)

        self._client = redis.Redis(
            host=self.__host,
            port=self.__port,
            password=self.__password,
            db=self.__default_path[0]
        )

    async def get(self, key: str) -> Opt[typing.Any]:
        return self._client.get(key)

    async def push(self, queue: str, item: typing.Any) -> None:
        await self._client.lpushx(queue, item)

    async def pop(self, queue: str) -> typing.Any:
        return await self._client.lpop(queue)

    async def pop_and_push(self, queue: str, dst_queue: str) -> typing.Any:
        return await self._client.rpoplpush(queue, dst_queue)

    async def blocking_pop_and_push(
        self,
        queue: str,
        dst_queue: str,
        timeout: float = 0
    ) -> typing.Any:
        return await self._client.brpoplpush(queue, dst=dst_queue, timeout=timeout)
