"""BlueFirmament Event Bus.

The EventBus is responsible for:
- Registering event handlers
- Emitting events to handlers
- Applying middleware before handlers
"""

__all__ = [
    "EventBus",
    "EventHandler",
    "on_event",
]

import asyncio
import re
import typing
from typing import Optional as Opt

from .main import Event, EventID
from .middleware import BaseMiddleware, MiddlewaresT
from ..utils.main import call_as_async
from ..log import get_logger

if typing.TYPE_CHECKING:
    from structlog.stdlib import BoundLogger


LOGGER = get_logger(__name__)


type EventHandlerFunc = typing.Callable[
    [Event], typing.Union[None, typing.Coroutine[typing.Any, typing.Any, None]]
]
"""Type for event handler functions."""


class EventHandler(BaseMiddleware):
    """Wrapper for event handler functions.

    EventHandler wraps a function to handle events matching a pattern.
    It implements BaseMiddleware to participate in the middleware chain.
    """

    def __init__(
        self,
        func: EventHandlerFunc,
        event_pattern: str,
    ):
        """Initialize event handler.

        Args:
            func: The handler function
            event_pattern: Regex pattern for events to handle
        """
        super().__init__(event_pattern=event_pattern)
        self._func = func
        self._pattern_str = event_pattern

    @property
    def pattern(self) -> str:
        """The event pattern string."""
        return self._pattern_str

    async def __call__(
        self,
        *,
        next_: typing.Any = None,
        event: Event = None,
        context: typing.Optional[typing.Any] = None,
        task_context: typing.Any = None,
    ) -> None:
        """Execute the handler function.

        Args:
            next_: Ignored for handlers (they are the end of the chain)
            event: The event to handle
            context: Optional context object
            task_context: Task context (for task-based middleware compatibility)
        """
        await call_as_async(self._func, event)
        # Call next if provided (for middleware chain compatibility)
        if next_ is not None:
            await next_()


class EventBus:
    """Event Bus for managing event handlers and emitting events.

    The EventBus provides:
    - Handler registration with pattern matching
    - Event emission with middleware chain
    - Pattern-based middleware application

    Example:
        ```python
        bus = EventBus()

        # Register middleware
        bus.use(LoggingMiddleware())

        # Register handler
        @bus.on("user.*")
        async def handle_user_events(event: Event):
            print(f"User event: {event.id}")

        # Emit event
        await bus.emit(Event.create("user.created", {"user_id": 123}))
        ```
    """

    def __init__(
        self,
        name: str = "default",
        middlewares: Opt[MiddlewaresT] = None,
    ):
        """Initialize the event bus.

        Args:
            name: Name of this event bus
            middlewares: Initial list of middlewares
        """
        self._name = name
        self._handlers: list[EventHandler] = []
        self._middlewares: MiddlewaresT = middlewares or []
        self._logger: "BoundLogger" = LOGGER.bind(event_bus=name)

    @property
    def name(self) -> str:
        """Name of this event bus."""
        return self._name

    @property
    def handlers(self) -> list[EventHandler]:
        """Registered event handlers."""
        return self._handlers

    @property
    def middlewares(self) -> MiddlewaresT:
        """Registered middlewares."""
        return self._middlewares

    def use(self, middleware: BaseMiddleware) -> "EventBus":
        """Add a middleware to the event bus.

        Args:
            middleware: The middleware to add

        Returns:
            self for chaining
        """
        self._middlewares.append(middleware)
        return self

    def register(
        self,
        pattern: str,
        handler: EventHandlerFunc,
    ) -> EventHandler:
        """Register an event handler.

        Args:
            pattern: Regex pattern for events to handle
            handler: The handler function

        Returns:
            The created EventHandler
        """
        event_handler = EventHandler(func=handler, event_pattern=pattern)
        self._handlers.append(event_handler)
        self._logger.debug(
            "Handler registered",
            pattern=pattern,
            handler=handler.__name__ if hasattr(handler, "__name__") else str(handler),
        )
        return event_handler

    def on(self, pattern: str) -> typing.Callable[[EventHandlerFunc], EventHandlerFunc]:
        """Decorator to register an event handler.

        Args:
            pattern: Regex pattern for events to handle

        Returns:
            Decorator function

        Example:
            ```python
            @bus.on(r"user\\..*")
            async def handle_user_events(event: Event):
                print(f"User event: {event.id}")
            ```
        """

        def decorator(func: EventHandlerFunc) -> EventHandlerFunc:
            self.register(pattern, func)
            return func

        return decorator

    def _find_handlers(self, event: Event) -> list[EventHandler]:
        """Find all handlers matching an event.

        Args:
            event: The event to match

        Returns:
            List of matching handlers
        """
        return [h for h in self._handlers if h.matches_event(event)]

    async def emit(
        self,
        event: Event,
        context: typing.Optional[typing.Any] = None,
    ) -> None:
        """Emit an event to all matching handlers.

        The event passes through all matching middlewares before
        reaching handlers. Multiple handlers can run concurrently.

        Args:
            event: The event to emit
            context: Optional context for sharing state
        """
        self._logger.info(
            "Event emitted",
            event_id=str(event.id),
            trace_id=event.trace_id,
        )

        # Find matching handlers
        handlers = self._find_handlers(event)

        if not handlers:
            self._logger.debug("No handlers found for event", event_id=str(event.id))
            return

        # Build middleware chain with handlers at the end
        # Handlers are wrapped to run concurrently
        async def run_handlers() -> None:
            if len(handlers) == 1:
                await handlers[0](event=event, context=context)
            else:
                await asyncio.gather(
                    *(h(event=event, context=context) for h in handlers)
                )

        # Create handler middleware that calls all handlers
        class HandlerRunner(BaseMiddleware):
            def __init__(self_):
                super().__init__(event_pattern=None)

            async def __call__(
                self_,
                *,
                next_: typing.Any = None,
                event: Event = None,
                context: typing.Optional[typing.Any] = None,
                task_context: typing.Any = None,
            ) -> None:
                await run_handlers()

        # Filter middlewares that match this event and add handler runner
        matching_middlewares: MiddlewaresT = [
            m for m in self._middlewares if m.matches_event(event)
        ]
        matching_middlewares.append(HandlerRunner())

        # Run middleware chain
        await BaseMiddleware.run_middlewares(
            matching_middlewares,
            event=event,
            context=context,
        )

        self._logger.debug(
            "Event handled",
            event_id=str(event.id),
            handlers_count=len(handlers),
        )


def on_event(
    pattern: str,
    bus: Opt[EventBus] = None,
) -> typing.Callable[[EventHandlerFunc], EventHandlerFunc]:
    """Decorator to register an event handler on the default or specified bus.

    This is a convenience function for registering handlers without
    direct access to the event bus instance.

    Args:
        pattern: Regex pattern for events to handle
        bus: Optional event bus (uses default if not specified)

    Returns:
        Decorator function

    Example:
        ```python
        @on_event(r"user\\..*")
        async def handle_user_events(event: Event):
            print(f"User event: {event.id}")
        ```
    """

    def decorator(func: EventHandlerFunc) -> EventHandlerFunc:
        if bus is not None:
            bus.register(pattern, func)
        else:
            # Store pattern for later registration
            if not hasattr(func, "_event_patterns"):
                func._event_patterns = []
            func._event_patterns.append(pattern)
        return func

    return decorator
