import asyncio
import typing
from typing import Optional as Opt

from .._types import EventRegistriesT
from ..event.context import CommonEventContext
from ..event.context import ExtendedEventContext, BaseEventContext
from ..log.main import get_logger
from ..event.result import EventResult
from ..event.source.base import (
    BaseEventSource, BaseEventSource
)
from ..event import Event
from ..event.registry import EventRegistry
from .middleware import BaseMiddleware, MiddlewaresT
from blue_firmament.dal.query_components.filters import *

if typing.TYPE_CHECKING:
    from structlog.stdlib import BoundLogger
    from ..manager import BaseManager


class BlueFirmamentApp:

    def __init__(
        self,
        name: str = "",
        registries: Opt[EventRegistriesT] = None,
        event_sources: Opt[typing.Iterable[BaseEventSource]] = None,
        middlewares: Opt[MiddlewaresT] = None,
        event_context_cls: type[ExtendedEventContext] = CommonEventContext,
    ):
        """
        :param registries:
            If None, will create an empty registry for each event source.
        """
        self.__event_sources: set[BaseEventSource] = set(event_sources or ())
        self.__event_registries: EventRegistriesT = registries or {
            event_source: EventRegistry(name=str(event_source))
            for event_source in self.__event_sources
        }
        self.__event_context_cls: type[ExtendedEventContext] = event_context_cls
        self.__middlewares: MiddlewaresT = middlewares or []
        self.__logger = get_logger(f"BFApp[{name}]").bind(
            app_name=name
        )

    @property
    def _logger(self) -> "BoundLogger":
        return self.__logger

    def add_event_source(
        self,
        event_source: BaseEventSource,
        registry: Opt[EventRegistry] = None
    ):
        """Add an event source and its EventRegistry.
        """
        self.__event_sources.add(event_source)
        self.__event_registries[event_source] = registry or EventRegistry(
            name=event_source.name
        )

    # Alias for backward compatibility
    

    def add_manager(self, manager: type["BaseManager"]):
        """Merge the manager's task registries.
        """
        for event_source, event_entry in manager.__event_registries__.items():
            self.__event_registries[event_source].merge(event_entry)

    def add_managers(self, *managers: type["BaseManager"]):
        for manager in managers:
            self.add_manager(manager)

    def run(self):
        """Start the application.
        """
        event_loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(event_loop)

            for transport in self.__event_sources:
                event_loop.create_task(transport.start())
            
            event_loop.run_forever()
        except KeyboardInterrupt:
            self._logger.info('Stop for KeyboardInterrupt')
        finally:
            event_loop.stop()
            event_loop.close()

    async def handle_event(
        self,
        event_source: BaseEventSource | str,
        event: Event,
        event_result: EventResult
    ):
        event_entry = self.__event_registries[event_source].lookup(task.id)
        middlewares: MiddlewaresT = self.__middlewares + [event_entry]
        event_context = self.__event_context_cls(BaseEventContext(
            task=task,
            event_result=event_result,
            base_logger=self._logger
        ))
        BaseEventContext.set_contextvar(event_context)
        await BaseMiddleware.run_middlewares(middlewares, event_context)
