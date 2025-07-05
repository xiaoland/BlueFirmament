import asyncio
from typing import Optional as Opt


from .._types import TaskRegistriesT
from ..task.context import CommonTaskContext
from ..task.context import ExtendedTaskContext, BaseTaskContext
from ..log.main import get_logger
from ..task.result import TaskResult
from ..transport.base import (
    BaseTransporter
)
from ..task import TaskID, Task
from ..task.registry import TaskRegistry
from .middleware import BaseMiddleware, MiddlewaresT
from ..dal.filters import *

if typing.TYPE_CHECKING:
    from structlog.stdlib import BoundLogger
    from ..manager import BaseManager


class BlueFirmamentApp:

    def __init__(
        self,
        name: str = "",
        registries: Opt[TaskRegistriesT] = None,
        transporters: Opt[typing.Iterable[BaseTransporter]] = None,
        middlewares: Opt[MiddlewaresT] = None,
        task_context_cls: type[ExtendedTaskContext] = CommonTaskContext,
    ):
        """
        :param registries:
            If None, will create an empty registry for each transporter.
        """
        self.__transporters: set[BaseTransporter] = set(transporters) or set()
        self.__task_registries: TaskRegistriesT = registries or {
            transporter: TaskRegistry(name=str(transporter))
            for transporter in self.__transporters
        }
        self.__task_context_cls: type[ExtendedTaskContext] = task_context_cls
        self.__middlewares: MiddlewaresT = middlewares or []
        self.__logger = get_logger(f"BFApp[{name}]").bind(
            app_name=name
        )

    @property
    def _logger(self) -> "BoundLogger":
        return self.__logger

    def add_transporter(
        self,
        transporter: BaseTransporter,
        registry: Opt[TaskRegistry] = None
    ):
        """Add a transporter and its TaskRegistry.
        """
        self.__transporters.add(transporter)
        self.__task_registries[transporter] = registry or TaskRegistry(
            name=transporter.name
        )

    def add_manager(self, manager: type["BaseManager"]):
        """Merge the manager's task registries.
        """
        for transporter, task_entry in manager.__task_registries__.items():
            self.__task_registries[transporter].merge(task_entry)

    def add_managers(self, *managers: type["BaseManager"]):
        for manager in managers:
            self.add_manager(manager)

    def run(self):
        """Start the application.
        """
        event_loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(event_loop)

            for transport in self.__transporters:
                event_loop.create_task(transport.start())
            
            event_loop.run_forever()
        except KeyboardInterrupt:
            self._logger.info('Stop for KeyboardInterrupt')
        finally:
            event_loop.stop()
            event_loop.close()

    async def handle_task(
        self,
        transporter: BaseTransporter | str,
        task: Task,
        task_result: TaskResult
    ):
        task_entry = self.__task_registries[transporter].lookup(task.id)
        middlewares: MiddlewaresT = self.__middlewares + [task_entry]
        task_context = self.__task_context_cls(BaseTaskContext(
            task=task,
            task_result=task_result,
            base_logger=self._logger
        ))
        await BaseMiddleware.run_middlewares(middlewares, task_context)
