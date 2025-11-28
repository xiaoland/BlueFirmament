"""BlueFirmament Application Module

This module contains the main application class that coordinates
event sources and the event bus.
"""

import asyncio
import typing
from typing import Optional as Opt

from .event.context import CommonEventContext
from .event.context import ExtendedEventContext
from .log.main import get_logger
from .event.source.base import BaseEventSource
from .event import EventBus
from .event.middleware import MiddlewaresT

if typing.TYPE_CHECKING:
    from structlog.stdlib import BoundLogger
    from .manager import BaseManager


class BlueFirmamentApp:
    """BlueFirmament Application

    The main application class that manages event sources and
    a single shared event bus.
    """

    def __init__(
        self,
        name: str = "",
        event_bus: Opt[EventBus] = None,
        event_sources: Opt[typing.Iterable[BaseEventSource]] = None,
        middlewares: Opt[MiddlewaresT] = None,
        event_context_cls: type[ExtendedEventContext] = CommonEventContext,
    ):
        """
        :param name: Name of the application.
        :param event_bus: The event bus for this application.
            If None, a new event bus will be created.
        :param event_sources: Iterable of event sources to add to the app.
        :param middlewares: List of global middlewares to run for all events.
        :param event_context_cls: Class to use for creating event contexts.
        """
        self.__name = name
        self.__middlewares: MiddlewaresT = middlewares or []
        self.__event_context_cls: type[ExtendedEventContext] = event_context_cls
        self.__event_bus: EventBus = event_bus or EventBus(
            name=f"{name}_bus",
            middlewares=self.__middlewares,
            event_context_cls=self.__event_context_cls
        )
        self.__event_sources: set[BaseEventSource] = set(event_sources or ())
        self.__logger = get_logger(f"BFApp[{name}]").bind(
            app_name=name
        )

    @property
    def _logger(self) -> "BoundLogger":
        return self.__logger

    @property
    def name(self) -> str:
        return self.__name

    @property
    def event_bus(self) -> EventBus:
        """The application's event bus."""
        return self.__event_bus

    def add_event_source(self, event_source: BaseEventSource):
        """Add an event source to the application.

        :param event_source: The event source to add
        """
        self.__event_sources.add(event_source)

    def add_manager(self, manager: type["BaseManager"]):
        """Merge the manager's event bus entries into the app's event bus.
        """
        for event_bus in manager.__event_registries__.values():
            self.__event_bus.merge(event_bus)

    def add_managers(self, *managers: type["BaseManager"]):
        """Add multiple managers to the app."""
        for manager in managers:
            self.add_manager(manager)

    def run(self):
        """Start the application.

        This runs all event sources in an asyncio event loop.
        """
        event_loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(event_loop)

            for event_source in self.__event_sources:
                event_loop.create_task(event_source.start())

            event_loop.run_forever()
        except KeyboardInterrupt:
            self._logger.info('Stop for KeyboardInterrupt')
        finally:
            event_loop.stop()
            event_loop.close()
