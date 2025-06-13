"""BlueFirmament Middleware"""

__all__ = [
    "BaseMiddleware",
]

import abc
import typing
from ..utils import call_as_async
if typing.TYPE_CHECKING:
    from blue_firmament.task.context import BaseTaskContext


type NextT = typing.Callable[[], typing.Coroutine[typing.Any, typing.Any, None]]
type MiddlewaresT = typing.List['BaseMiddleware']


class BaseMiddleware(abc.ABC):
    """Base class of BlueFirmament Middleware.
    """

    @abc.abstractmethod
    def __call__(self, *, next: NextT, task_context: 'BaseTaskContext') -> typing.Union[
        None, typing.Coroutine
    ]:
        pass

    @staticmethod
    def run_middlewares(middlewares: MiddlewaresT, task_context: "BaseTaskContext"):
        return call_as_async(
            middlewares[0], 
            next=BaseMiddleware._get_next(middlewares, task_context=task_context), 
            task_context=task_context
        )

    @staticmethod
    def _get_next(
        middlewares: MiddlewaresT, task_context: "BaseTaskContext",
        current: int = 0
    ) -> NextT:
        async def _next() -> None:
            nonlocal current
            current += 1
            if current < len(middlewares):
                return await call_as_async(
                    middlewares[current],
                    next=BaseMiddleware._get_next(
                        middlewares, task_context=task_context, current=current
                    ),
                    task_context=task_context
                )
            else:
                return None
        return _next
