"""BlueFirmament Middleware.

Middleware provides a way to intercept and process events
before they reach their handlers.
"""

__all__ = [
    "BaseMiddleware",
    "MiddlewaresT",
    "NextT",
]

import abc
import re
import typing

from ..utils.main import call_as_async

if typing.TYPE_CHECKING:
    from .model import Event


type NextT = typing.Callable[[], typing.Coroutine[typing.Any, typing.Any, None]]
"""Type for the next function in middleware chain."""

type MiddlewaresT = typing.List["BaseMiddleware"]
"""Type for a list of middlewares."""


class BaseMiddleware(abc.ABC):
    """Base class of BlueFirmament Middleware.

    Middleware intercepts events before they reach their handlers,
    allowing for cross-cutting concerns like logging, authentication,
    validation, etc.

    Each middleware can optionally specify an event pattern to match.
    Only events matching the pattern will be processed by this middleware.
    """

    def __init__(
        self,
        event_pattern: typing.Optional[str] = None,
    ):
        """Initialize middleware.

        Args:
            event_pattern: Optional regex pattern to match event IDs.
                If None, middleware applies to all events.
        """
        self._event_pattern: typing.Optional[re.Pattern] = None
        if event_pattern:
            self._event_pattern = re.compile(event_pattern)

    def matches_event(self, event: "Event") -> bool:
        """Check if this middleware should process the given event.

        Args:
            event: The event to check

        Returns:
            True if middleware should process this event
        """
        if self._event_pattern is None:
            return True
        return bool(self._event_pattern.match(str(event.id)))

    @abc.abstractmethod
    def __call__(
        self,
        *,
        next_: NextT,
        event: "Event",
        context: typing.Optional[typing.Any] = None,
    ) -> typing.Union[None, typing.Coroutine]:
        """Process the event.

        Args:
            next_: Function to call the next middleware/handler
            event: The event being processed
            context: Optional context object for sharing state
        """
        ...

    @staticmethod
    async def run_middlewares(
        middlewares: MiddlewaresT,
        event: "Event",
        context: typing.Optional[typing.Any] = None,
    ) -> None:
        """Run a chain of middlewares for an event.

        Only middlewares that match the event pattern will be executed.

        Args:
            middlewares: List of middlewares to run
            event: The event to process
            context: Optional context for sharing state
        """
        # Filter middlewares that match this event
        matching_middlewares = [m for m in middlewares if m.matches_event(event)]

        if not matching_middlewares:
            return

        await call_as_async(
            matching_middlewares[0],
            next_=BaseMiddleware._get_next(
                matching_middlewares,
                event=event,
                context=context,
            ),
            event=event,
            context=context,
        )

    @staticmethod
    def _get_next(
        middlewares: MiddlewaresT,
        event: "Event",
        context: typing.Optional[typing.Any] = None,
        current: int = 0,
    ) -> NextT:
        """Get the next function for the middleware chain.

        Args:
            middlewares: List of middlewares
            event: The event being processed
            context: Optional context object
            current: Current position in middleware chain
        """

        async def _next() -> None:
            nonlocal current
            current += 1
            if current < len(middlewares):
                return await call_as_async(
                    middlewares[current],
                    next_=BaseMiddleware._get_next(
                        middlewares,
                        event=event,
                        context=context,
                        current=current,
                    ),
                    event=event,
                    context=context,
                )
            else:
                return None

        return _next
