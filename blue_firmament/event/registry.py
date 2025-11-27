"""Event registry module (formerly Task registry).
"""

__all__ = [
    'EventRegistry',
    'EventEntry',
    'listen_to'
]

import asyncio
import copy
import inspect
import typing
from typing import Optional as Opt, Annotated as Anno, Literal as Lit

from ..exceptions import EventHandlerNotFound
from .._types import PathParamsT, CallableTV
from .source.base import BaseEventSource, BaseEventSource
from .result import Body, JsonBody
from .context import BaseEventContext
from ..core.middleware import BaseMiddleware
from .main import EventID, Method
from . import EventHandler
from ..utils.inspect_ import get_param_types

if typing.TYPE_CHECKING:
    from ..manager import BaseManager


class EventEntry(BaseMiddleware):
    """BlueFirmament EventEntry

    A mapping from EventID to a couple of EventHandler(s).

    Work as a middleware, run this middleware will concurrently
    run all handlers in this entry.

    Can be stored as key in dict or element in set.

    :ivar path_params: Path parameters resolved from the looked up EventID.
        Will be set on the copy of this entry.
    """

    def __init__(
        self,
        event_id: EventID,
        *handlers: EventHandler | typing.Callable
    ) -> None:
        self.__event_id = event_id
        self.__handlers: typing.List[EventHandler] = list(
            handler if isinstance(handler, EventHandler) else EventHandler(function=handler)
            for handler in handlers
        )
        self.path_params: dict[str, PathParamsT] = {}

    @property
    def id(self):
        return self.__event_id

    @property
    def handlers(self):
        return self.__handlers

    def fork(
        self,
        path_prefix: str = ""
    ) -> typing.Self:
        """Fork this entry with a new EventID

        :param path_prefix:
            Prefix event_id path with this.
        :return: Forked EventEntry
        """
        return EventEntry(
            self.__event_id.fork(
                path_prefix=path_prefix
            ),
            *self.__handlers
        )

    def is_dynamic(self) -> bool:
        return self.__event_id.is_dynamic()

    def is_match(self, event_id: EventID) -> Opt[dict]:
        """Whether a event_id match this entry's event_id
        """
        return self.__event_id.is_match(event_id)

    def add_handler(self, task_handler: EventHandler):
        """Add a EventHandler
        """
        self.__handlers.append(task_handler)

    def set_manager_cls(self, manager_cls: typing.Type["BaseManager"]):
        """Set manager class for all handlers in this entry.
        """
        for handler in self.__handlers:
            handler.set_manager_cls(manager_cls)

    async def __call__(self, *, next_, event_context: 'BaseEventContext'):
        """Run all handlers in this entry concurrently.

        If multiple results, set event result body to a JsonBody which is a list
        wrapped those results.
        If only one result (where when one handler), set event result body to it.
        """
        coros: list[typing.Awaitable[Body]] = []
        for handler in self.__handlers:
            coros.append(handler(
                event_context=event_context, path_params=self.path_params
            ))

        results = await asyncio.gather(*coros)

        if len(results) == 1:
            event_context._event_result.body = results[0]
        else:
            event_context._event_result.body = JsonBody([
                result
                for result in results
            ])

        await next_()


class EventRegistry:
    """BlueFirmament Event Registry

    A bunch of task entries that you can look up by EventID.
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
        self.__static_entries: dict[EventID, EventEntry] = dict()
        self.__dynamic_entries: list[EventEntry] = list()
        self.__path_prefix = path_prefix
        self.__name = name

    @property
    def name(self): return self.__name
    @property
    def static_entries(self): return self.__static_entries
    @property
    def dynamic_entries(self): return self.__dynamic_entries

    def add_entry(self, entry: EventEntry):
        entry = entry.fork(path_prefix=self.__path_prefix)
        if not entry.is_dynamic():
            self.__static_entries[entry.id] = entry
        else:
            self.__dynamic_entries.append(entry)

    def add_entries(self, entries: typing.Iterable[EventEntry]):
        for entry in entries:
            self.add_entry(entry)
        
    def add_handler(
        self,
        method: Opt[Method] = None,
        path: Opt[str] = None,
        event_id: Opt[EventID] = None,
        handler: Opt[EventHandler] = None,
        function: Opt[typing.Callable] = None,
        handler_manager_cls: Opt[typing.Type["BaseManager"]] = None,
    ):
        """Bind a event handler to Event(ID).

        :param method:
        :param path: 
            Must start with a slash and ends with no slash.
        :param event_id:
            Replace method and path and path_prefix won't be applied.
        :param handler: A event handler.
        """
        if handler is None:
            if not (function is None or handler_manager_cls is None):
                handler = EventHandler(
                    function=function,
                    manager_cls=handler_manager_cls
                )
            else:
                raise ValueError("provide handler or inner_handler and handler_manager")
        
        if event_id is None:
            if not (method is None or path is None):
                event_id = EventID(
                    method, self.__path_prefix + path,
               )
            else:
                raise ValueError("provide event_id or method and path")

        try:
            if not event_id.is_dynamic():
                entry = self.lookup(event_id)
            else:
                # lookup in dynamic entries
                entry = next(
                    (e for e in self.__dynamic_entries if e.is_match(event_id)),
                    None
                )
            if entry is None:
                raise KeyError
        except KeyError:
            # no such entry, create one
            entry = EventEntry(event_id, handler)

        if not event_id.is_dynamic():
            self.__static_entries[entry.id] = entry
        else:
            self.__dynamic_entries.append(entry)

    def merge(self, to_merge: "EventRegistry"):
        """Merge another event registry's entries.

        Every entry to be merged will be prefixed with the path_prefix.
        (Of course on the forked entry)
        """
        for entry in to_merge.static_entries.values():
            entry = entry.fork(self.__path_prefix)
            self.__static_entries[entry.id] = entry
        for entry in to_merge.dynamic_entries:
            entry = entry.fork(self.__path_prefix)
            self.__dynamic_entries.append(entry)

    def lookup(
        self,
        event_id: EventID,
    ) -> EventEntry:
        """Lookup a task entry by event_id.

        :param event_id: The task ID to lookup, must be static.
        :raise NotFound: If no task entry matched.
        :raise TypeError: If event_id is dynamic.
        :returns:
            The (shallow) copy of the matched EventEntry
            with path_params set.
        """
        if event_id.is_dynamic(allow_method_dynamic=True):
            raise TypeError("Cannot lookup a dynamic event_id")

        entry = self.__static_entries.get(event_id, None)
        if entry is not None:
            return entry
        else:
            # lookup in dynamic entries
            for entry in self.__dynamic_entries:
                match_res = entry.is_match(event_id)
                if match_res is not None:
                    entry = copy.copy(entry)
                    entry.path_params = match_res
                    return entry
                else:
                    continue

        raise EventHandlerNotFound(
            event_id=event_id,
        )


def listen_to(
    method: Opt[Method | str],
    path: str,
    separator: str = "/",
    event_sources: Opt[typing.Iterable[str | BaseEventSource]] = None,
):
    """Make the function a handler to an event.

    :param event_sources:
        Only events from these event sources will be handled by this handler.
        None for default event source (you must have an event source named "default").

    Will wrap decorated function to a EventEntry.
    With support of :meth:`blue_firmament.manager.ManagerMetaclass`,
    this entry will be added to manager event registry.
    Finally, with :meth:`blue_firmament.event.EventRegistry.merge` or
    :meth:`blue_firmament.core.BlueFirmamentApp.add_manager`,
    manager event registry's entries will be merged into application
    event registry.
    """
    def wrapper(handler: CallableTV) -> CallableTV:
        return typing.cast(CallableTV, (
            tuple(event_sources or ("default",)),
            EventEntry(
                EventID(
                    method=method, path=path,
                    separator=separator,
                    param_types=get_param_types(handler),
                ),
                handler
            )
        )) # lie to type checker
    return wrapper
