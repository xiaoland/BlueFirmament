"""BlueFirmament Middleware"""

__all__ = [
    "BaseMiddleware",
    "NextT",
    "MiddlewaresT",
]

import abc
import typing
from ..utils.main import call_as_async

if typing.TYPE_CHECKING:
    from blue_firmament.event.context import BaseEventContext


NextT = typing.Callable[[], typing.Coroutine[typing.Any, typing.Any, None]]
MiddlewaresT = typing.List['BaseMiddleware']


class BaseMiddleware(abc.ABC):
    """Base class of BlueFirmament Middleware.
    """

    @abc.abstractmethod
    def __call__(self, *, next_: NextT, event_context: 'BaseEventContext') -> typing.Union[
        None, typing.Coroutine
    ]:
        ...

    @staticmethod
    def run_middlewares(middlewares: MiddlewaresT, event_context: "BaseEventContext"):
        return call_as_async(
            middlewares[0], 
            next_=BaseMiddleware._get_next(middlewares, event_context=event_context), 
            event_context=event_context
        )

    @staticmethod
    def _get_next(
        middlewares: MiddlewaresT, event_context: "BaseEventContext",
        current: int = 0
    ) -> NextT:
        async def _next() -> None:
            nonlocal current
            current += 1
            if current < len(middlewares):
                return await call_as_async(
                    middlewares[current],
                    next_=BaseMiddleware._get_next(
                        middlewares, event_context=event_context, current=current
                    ),
                    event_context=event_context
                )
            else:
                return None
        return _next
