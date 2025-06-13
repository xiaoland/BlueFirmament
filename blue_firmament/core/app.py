import asyncio
from typing import Optional as Opt
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
    from ..manager import BaseManager


class BlueFirmamentApp:

    def __init__(
        self,
        name: str = 'noname',
        registry: Opt[TaskRegistry] = None,
        transporters: Opt[typing.List[BaseTransporter]] = None,
        middlewares: Opt[MiddlewaresT] = None,
        task_context_cls: typing.Type[ExtendedTaskContext] = CommonTaskContext,
    ):
        """
        :param registry: Task Registry, if not provided, a new one will be created.
        """
        self.__transporters: typing.List[BaseTransporter] = transporters or []
        self.__middlewares: MiddlewaresT = middlewares or []
        self.__task_registry: TaskRegistry = registry or TaskRegistry('root')
        self.__task_context_cls = task_context_cls
        self.__logger = get_logger(f"BlueFirmamentApp[{name}]").bind(
            app_name=name
        )

    @property
    def _logger(self): return self.__logger

    @property
    def task_registry(self) -> TaskRegistry:
        """获取应用根路由器实例"""
        return self.__task_registry

    def add_transporter(self, transporter: BaseTransporter):
        self.__transporters += (transporter,)

    def add_manager(self, manager: typing.Type["BaseManager"]):
        self.task_registry.merge(manager.__task_registry__)

    def run(self):
        """Start listening on added transporter.
        """
        event_loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(event_loop)

            for transport in self.__transporters:
                event_loop.create_task(transport.start_listening())
            
            event_loop.run_forever()
        except KeyboardInterrupt:
            self._logger.info('Stop for KeyboardInterrupt')
        finally:
            event_loop.stop()
            event_loop.close()

    def find_handlers(self, task_id: TaskID):
        return self.__task_registry.lookup(task_id)

    async def handle_task(self, task: Task, task_result: TaskResult):
        task_entry = self.task_registry.lookup(task.id)
        middlewares: MiddlewaresT = self.__middlewares + [
            task_entry
        ]
        task_context = self.__task_context_cls(BaseTaskContext(
            task=task,
            task_result=task_result,
            base_logger=self._logger
        ))
        await BaseMiddleware.run_middlewares(middlewares, task_context)
