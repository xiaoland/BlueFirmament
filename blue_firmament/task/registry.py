"""Task registry module.
"""

__all__ = [
    'TaskRegistry',
    'TaskEntry',
    'task'
]

import asyncio
import copy
import typing
from typing import Optional as Opt, Annotated as Anno, Literal as Lit

from .result import Body, JsonBody
from ..task.context import BaseTaskContext
from ..core.middleware import BaseMiddleware
from .main import TaskID, Method
from . import TaskHandler

if typing.TYPE_CHECKING:
    from ..manager import BaseManager


class TaskEntry(BaseMiddleware):
    """BlueFirmament TaskEntry

    A mapping from TaskID to a couple of TaskHandler(s).
    Work as a middleware, run this middleware will concurrently
    run all handlers in this entry.

    Can be stored as key in dict or element in set.

    :ivar path_params: Path parameters resolved from the looked up TaskID.
        Will be set on copy of this entry, not the original one.
    """

    def __init__(self,
        task_id: TaskID,
        *handlers: TaskHandler
    ) -> None:
        self.__task_id = task_id
        self.__handlers: typing.List[TaskHandler] = list(*handlers)
        self.path_params: dict[str, str] = {}

    @property
    def handlers(self):
        return self.__handlers

    def __hash__(self):
        return hash(self.__task_id)

    def __eq__(self, other):
        return other == self.__task_id

    def fork(
        self,
        path_prefix: Opt[str] = None
    ) -> typing.Self:
        """Fork this entry with a new TaskID

        :param path_prefix:
            Prefix task_id path with this.
        :return: Forked TaskEntry
        """
        return TaskEntry(
            task_id=self.__task_id.fork(
                path_prefix=path_prefix
            ),
            *self.__handlers
        )

    def is_dynamic(self) -> bool:
        return self.__task_id.is_dynamic()

    def is_match(self, task_id: TaskID) -> Opt[dict]:
        """Whether a task_id match this entry's task_id
        """
        return self.__task_id.is_match(task_id)

    def add_handler(self, task_handler: TaskHandler):
        """Add a TaskHandler
        """
        self.__handlers.append(task_handler)

    def set_manager_cls(self, manager_cls: typing.Type["BaseManager"]):
        """Set manager class for all handlers in this entry.
        """
        for handler in self.__handlers:
            handler.set_manager_cls(manager_cls)

    async def __call__(self, *, next, task_context: 'BaseTaskContext'):
        """Run all handlers in this entry concurrently.

        If multiple results, set task result body to a JsonBody which is a list
        wrapped those results.
        If only one result (where when one handler), set task result body to it.
        """
        coros: list[typing.Awaitable[Body]] = []
        for handler in self.__handlers:
            coros.append(handler(
                task_context=task_context, path_params=self.path_params
            ))

        results = await asyncio.gather(*coros)

        if len(results) == 1:
            task_context._task_result.body = results[0]
        else:
            task_context._task_result.body = JsonBody([
                result
                for result in results
            ])

        await next()


class TaskRegistry:
    """BlueFirmament Task Registry

    A bunch of task entries that you can look up by TaskID.
    """

    def __init__(self, 
        name: str = 'router',
        path_prefix: str = ''
    ):
        """
        :param path_prefix: 
            Prefix added to every record path
            registered to this router.

            Can be ``/abc/{var}`` or ``abc/{var}``, but don't
            end with a slash.
        """
        self.__static_entries: set[TaskEntry] = set()
        self.__dynamic_entries: list[TaskEntry] = list()
        self.__path_prefix = path_prefix
        self.__name = name

    @property
    def name(self): return self.__name
    @property
    def static_entries(self): return self.__static_entries
    @property
    def dynamic_entries(self): return self.__dynamic_entries

    def add_entry(self, entry: TaskEntry):
        if not entry.is_dynamic():
            self.__static_entries.add(entry)
        else:
            self.__dynamic_entries.append(entry)
        
    def add_handler(
        self,
        method: Opt[Method] = None,
        path: Opt[str] = None,
        task_id: Opt[TaskID] = None,
        handler: Opt[TaskHandler] = None,
        inner_handler: Opt[typing.Callable] = None,
        handler_manager_cls: Opt[typing.Type["BaseManager"]] = None,
    ):
        """Bind a task handler to Task(ID).

        :param method:
        :param path: 
            Must start with a slash and ends with no slash.
        :param task_id:
            Replace method and path and path_prefix won't be applied.
        :param handler: A task handler.
        """
        if handler is None:
            if not (inner_handler is None or handler_manager_cls is None):
                handler = TaskHandler(
                    inner_handler=inner_handler,
                    manager_cls=handler_manager_cls
                )
            else:
                raise ValueError("provide handler or inner_handler and handler_manager")
        
        if task_id is None:
            if not (method is None or path is None):
                task_id = TaskID(
                    method, self.__path_prefix + path,
               )
            else:
                raise ValueError("provide task_id or method and path")

        try:
            if not task_id.is_dynamic():
                entry = self.lookup(task_id)
            else:
                # lookup in dynamic entries
                entry = next(
                    (e for e in self.__dynamic_entries if e.is_match(task_id)),
                    None
                )
            if entry is None:
                raise KeyError
        except KeyError:
            # no such entry, create one
            entry = TaskEntry(task_id, handler)

        if not task_id.is_dynamic():
            self.__static_entries.add(entry)
        else:
            self.__dynamic_entries.append(entry)

    def merge(self, to_merge: "TaskRegistry"):
        """Merge another task registry's entries.

        Every entry to be merged will be prefixed with the path_prefix.
        (Of course on the forked entry)
        """
        for entry in to_merge.static_entries:
            self.__static_entries.add(entry.fork(self.__path_prefix))
        for entry in to_merge.dynamic_entries:
            self.__dynamic_entries.append(entry.fork(self.__path_prefix))

    def lookup(self, task_id: TaskID) -> TaskEntry:
        """Lookup a task entry by task_id.

        :param task_id: The task ID to lookup, must be static.
        :raise KeyError: If no task entry matched.
        :raise TypeError: If task_id is dynamic.
        :returns: The (shallow) copy of the TaskEntry that matches the task_id
            and with path_params set.
        """
        if task_id.is_dynamic():
            raise TypeError("Cannot lookup a dynamic task_id")

        intersection = self.__static_entries.intersection({task_id})
        if intersection:
            return intersection.pop()
        else:
            # lookup in dynamic entries
            for entry in self.__dynamic_entries:
                match_res = entry.is_match(task_id)
                if match_res is not None:
                    entry = copy.copy(entry)
                    entry.path_params = match_res
                    return entry
                else:
                    continue

        raise KeyError(f"TaskID {task_id} don't has an entry in registry {self.name}")


CallableTV = typing.TypeVar("CallableTV", bound=typing.Callable)
def task(
    method: Opt[Method],
    path: Opt[str],
    separator: Opt[str] = "/",
    task_id: Opt[TaskID] = None
):
    """Mark a function as a handler of a task.

    :param method:
    :param path:
    :param separator:
    :param task_id: If provided, will override method and path.

    Will wrap decorated function to a TaskEntry.
    With support of :meth:`blue_firmament.manager.ManagerMetaclass`,
    this entry will be added to manager task registry.
    Finally, with :meth:`blue_firmament.task.TaskRegistry.merge` or
    :meth:`blue_firmament.core.BlueFirmamentApp.add_manager`,
    manager task registry's entries will be merged into application
    task registry.
    """
    def wrapper(handler: CallableTV) -> CallableTV:
        return typing.cast(CallableTV, TaskEntry(
            TaskID(method=method, path=path, separator=separator) \
                if task_id is None else task_id,
            handler
        )) # tricked type checker
    return wrapper
