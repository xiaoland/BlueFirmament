"""BlueFirmament Dependency Injection framework
"""

import inspect
import typing
from typing import Optional as Opt, Annotated as Anno, Literal as Lit

from .utils.main import call_as_sync
from .utils.inspect_ import args_to_kwargs_by_sig


class DependencyInjector:

    """
    :ivar pargs: Position only arguments
    :ivar kargs: Keyword or position arguments
    """

    class ArgGetterT(typing.Protocol):
        
        """A callable use to get the argument value.
        """

        def __call__(self,
            args: typing.Tuple[typing.Any], 
            kwargs: typing.Dict[str, typing.Any]
        ) -> typing.Any:
            
            """
            :param args: Positional arguments.
            :param kwargs: Keyword arguments.
            """
            ...

    class DynamicArgGetterT(typing.Protocol):

        """A callable use to get argument getter
        """

        def __call__(self, anno: typing.Type) -> "DependencyInjector.ArgGetterT":
            ...
    
    __getters_by_name__: typing.Mapping[str, ArgGetterT] = {}
    """A dictionary of argument name to getter function."""
    __getters_by_anno__: typing.Mapping[typing.Type, ArgGetterT] = {}
    """A dictionary of argument annotation to getter function."""
    __dgetters_by_name__: typing.Mapping[str, DynamicArgGetterT] = {}
    """A dictionary of argument name to dynamic getter function."""

    def __init__(self, 
        callable: typing.Callable,
        getters_by_name: Opt[typing.Mapping[str, ArgGetterT]] = None,
        getters_by_anno: Opt[typing.Mapping[typing.Type, ArgGetterT]] = None,
        dgetters_by_name: Opt[typing.Mapping[str, DynamicArgGetterT]] = None,
    ) -> None:

        """
        :param callable: The callable to be injected.

            - Can be async function. (run synchronously)
        :param getters_by_name: Override class level getters by name.
        :param getters_by_anno: Override class level getters by annotation.
        """

        self.__callable = callable
        if getters_by_name:
            self.__getters_by_name__ = getters_by_name
        if getters_by_anno:
            self.__getters_by_anno__ = getters_by_anno
        if dgetters_by_name:
            self.__dgetters_by_name__ = dgetters_by_name
        
        self.__pargs, self.__kargs = self._parse_args(callable)

    @property
    def name(self) -> str:
        return self.__callable.__qualname__

    def __call__(self, *rargs, **rkwargs) -> typing.Any:
        
        """Call the callable with the arguments.

        If argument has no getter, use raw value from args or kwargs.

        :param rargs: Positional only arguments.
        :param rkwargs: Keyword or positional arguments.

            Keyword arg that is not in the signature will be ignored.
        """
        args = list()
        kwargs = dict()
        for i, v in enumerate(self.__pargs):
            if v:
                args.append(v(rargs, rkwargs))
            else:
                try:
                    args.append(rargs[i])
                except IndexError:
                    continue
        for k, v in self.__kargs.items():
            if v:
                kwargs[k] = v(rargs, rkwargs)
            else:
                try:
                    kwargs[k] = rkwargs[k]
                except KeyError:
                    continue

        return call_as_sync(self.__callable, *args, **kwargs)

    def _parse_args(self, callable: typing.Callable) -> typing.Tuple[
        typing.Tuple[Opt[ArgGetterT], ...],
        typing.Dict[str, Opt[ArgGetterT]]
    ]:
        """
        
        """
        parameters_sig = inspect.signature(callable).parameters
        pargs = []
        kargs = {}
        for name, param in parameters_sig.items():
            getter = self._get_arg_getter(name, param.annotation)
            if param.kind == inspect.Parameter.POSITIONAL_ONLY:
                pargs.append(getter)
            elif param.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD:
                kargs[name] = getter

        return tuple(pargs), kargs
    
    def _get_arg_getter(self,
        name: str,
        anno: typing.Type,
    ) -> typing.Optional[ArgGetterT]:
        
        """Get the argument getter function.

        Priority:
        1. Getters by name
        2. Getters by annotation
        3. Dynamic getters by name

        :return: The argument getter function or None.
        """
        res = self.__getters_by_name__.get(name)
        if not res:
            res = self.__getters_by_anno__.get(anno)
        if not res:
            res_ = self.__dgetters_by_name__.get(name)
            if res_:
                res = res_(anno)

        return res

    def pargs_to_kwargs(self, *pargs) -> typing.Dict[str, typing.Any]:

        """Convert positional arguments to keyword arguments.

        :param pargs: Positional arguments.
        :return: Keyword arguments.
        """
        return args_to_kwargs_by_sig(self.__callable, *pargs)