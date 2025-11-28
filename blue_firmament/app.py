"""BlueFirmament Application Module

This module contains the main application class that coordinates
event sources and event buses.
"""

import asyncio
import typing
from typing import Optional as Opt

from ._types import EventBusesT
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

    The main application class that manages event sources and their
    associated event buses.
    """

    def __init__(
        self,
        name: str = "",
        event_buses: Opt[EventBusesT] = None,
        event_sources: Opt[typing.Iterable[BaseEventSource]] = None,
        middlewares: Opt[MiddlewaresT] = None,
        event_context_cls: type[ExtendedEventContext] = CommonEventContext,
    ):
        """
        :param name: Name of the application.
        :param event_buses: Mapping of event sources to their event buses.
            If None, will create an empty event bus for each event source.
        :param event_sources: Iterable of event sources to add to the app.
        :param middlewares: List of global middlewares to run for all events.
        :param event_context_cls: Class to use for creating event contexts.
        """
        self.__name = name
        self.__event_sources: set[BaseEventSource] = set(event_sources or ())
        self.__event_buses: EventBusesT = event_buses or {}
        self.__event_context_cls: type[ExtendedEventContext] = event_context_cls
        self.__middlewares: MiddlewaresT = middlewares or []
        self.__logger = get_logger(f"BFApp[{name}]").bind(
            app_name=name
        )

        # Create event buses for event sources that don't have one
        for event_source in self.__event_sources:
            if event_source not in self.__event_buses:
                self.__event_buses[event_source] = EventBus(
                    name=str(event_source),
                    middlewares=self.__middlewares,
                    event_context_cls=self.__event_context_cls
                )

    @property
    def _logger(self) -> "BoundLogger":
        return self.__logger

    @property
    def name(self) -> str:
        return self.__name

    def get_event_bus(self, event_source: BaseEventSource | str) -> EventBus:
        """Get the event bus for a specific event source.

        :param event_source: The event source or its name
        :return: The associated EventBus
        :raises KeyError: If no event bus exists for the event source
        """
        return self.__event_buses[event_source]

    def add_event_source(
        self,
        event_source: BaseEventSource,
        event_bus: Opt[EventBus] = None
    ):
        """Add an event source and its EventBus.

        :param event_source: The event source to add
        :param event_bus: Optional event bus. If None, creates a new one.
        """
        self.__event_sources.add(event_source)
        self.__event_buses[event_source] = event_bus or EventBus(
            name=event_source.name,
            middlewares=self.__middlewares,
            event_context_cls=self.__event_context_cls
        )

    def add_manager(self, manager: type["BaseManager"]):
        """Merge the manager's event buses into the app's event buses.
        """
        for event_source, event_bus in manager.__event_registries__.items():
            self.__event_buses[event_source].merge(event_bus)

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
