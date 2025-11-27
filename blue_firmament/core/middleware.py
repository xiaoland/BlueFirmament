"""BlueFirmament Task Middleware.

Task-specific middleware for processing tasks before handlers.
For event-based middleware, see :mod:`blue_firmament.event.middleware`.
"""

__all__ = [
    "BaseTaskMiddleware",
    "BaseMiddleware",  # Backward compatibility alias
    "TaskMiddlewaresT",
    "MiddlewaresT",  # Backward compatibility alias
]

import abc
import typing
from ..utils.main import call_as_async

if typing.TYPE_CHECKING:
    from blue_firmament.task.context import BaseTaskContext


type TaskNextT = typing.Callable[[], typing.Coroutine[typing.Any, typing.Any, None]]
type TaskMiddlewaresT = typing.List["BaseTaskMiddleware"]

# Backward compatibility aliases
type NextT = TaskNextT
type MiddlewaresT = TaskMiddlewaresT


class BaseTaskMiddleware(abc.ABC):
    """Base class for task middleware.

    Task middleware processes tasks before they reach handlers,
    allowing for cross-cutting concerns like logging, authentication,
    validation, etc.
    """

    @abc.abstractmethod
    def __call__(
        self, *, next_: TaskNextT, task_context: "BaseTaskContext"
    ) -> typing.Union[None, typing.Coroutine]: ...

    @staticmethod
    def run_middlewares(middlewares: TaskMiddlewaresT, task_context: "BaseTaskContext"):
        return call_as_async(
            middlewares[0],
            next_=BaseTaskMiddleware._get_next(middlewares, task_context=task_context),
            task_context=task_context,
        )

    @staticmethod
    def _get_next(
        middlewares: TaskMiddlewaresT, task_context: "BaseTaskContext", current: int = 0
    ) -> TaskNextT:
        async def _next() -> None:
            nonlocal current
            current += 1
            if current < len(middlewares):
                return await call_as_async(
                    middlewares[current],
                    next_=BaseTaskMiddleware._get_next(
                        middlewares, task_context=task_context, current=current
                    ),
                    task_context=task_context,
                )
            else:
                return None

        return _next


# Backward compatibility alias
BaseMiddleware = BaseTaskMiddleware
