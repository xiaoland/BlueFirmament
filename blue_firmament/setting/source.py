"""Setting Sources Module

SettingSource classes define where and how to load setting values.
"""

__all__ = [
    "SettingSource",
    "InlineSource",
    "EnvVarSource",
    "JsonFileSource",
    "PythonSource",
    "SourceValueTV",
]

import abc
import os
import typing
from pathlib import Path
from typing import Optional as Opt

from .._types import Undefined, _undefined
from ..utils.file import load_json_file
from ..utils.dict_ import get_nested_value


SourceValueTV = typing.TypeVar("SourceValueTV")


class SettingSource(abc.ABC, typing.Generic[SourceValueTV]):
    """Base class for setting sources.

    A SettingSource defines where and how to load a setting value.
    Sources are tried in order until one successfully returns a value.

    Attributes
    ----------
    priority : int
        Higher priority sources are tried first. Default is 0.
    converter : Callable[[Any], SourceValueTV] | None
        Optional converter to transform the raw value.
    """

    def __init__(
        self,
        priority: int = 0,
        converter: Opt[typing.Callable[[typing.Any], SourceValueTV]] = None,
    ):
        self._priority = priority
        self._converter = converter

    @property
    def priority(self) -> int:
        return self._priority

    @abc.abstractmethod
    def load(self) -> SourceValueTV | Undefined:
        """Load value from this source.

        Returns
        -------
        SourceValueTV | Undefined
            The loaded value, or _undefined if the source cannot provide a value.
        """
        ...

    def _apply_converter(self, value: typing.Any) -> SourceValueTV:
        """Apply converter if provided."""
        if self._converter is not None:
            return self._converter(value)
        return value


class InlineSource(SettingSource[SourceValueTV]):
    """Inline/hardcoded setting value source.

    Use this as a fallback default value.

    Example
    -------
    >>> InlineSource("default_value")
    >>> InlineSource(42, priority=-100)  # Low priority fallback
    """

    def __init__(
        self,
        value: SourceValueTV,
        priority: int = -100,  # Low priority by default
        converter: Opt[typing.Callable[[typing.Any], SourceValueTV]] = None,
    ):
        super().__init__(priority=priority, converter=converter)
        self._value = value

    def load(self) -> SourceValueTV:
        return self._apply_converter(self._value)

    def __repr__(self) -> str:
        return f"InlineSource({self._value!r})"


class EnvVarSource(SettingSource[SourceValueTV]):
    """Environment variable setting source.

    Example
    -------
    >>> EnvVarSource("DATABASE_URL")
    >>> EnvVarSource("DEBUG", converter=lambda x: x.lower() == "true")
    >>> EnvVarSource("PORT", converter=int, default=8080)
    """

    def __init__(
        self,
        env_var: str,
        default: SourceValueTV | Undefined = _undefined,
        priority: int = 100,  # High priority by default
        converter: Opt[typing.Callable[[typing.Any], SourceValueTV]] = None,
    ):
        super().__init__(priority=priority, converter=converter)
        self._env_var = env_var
        self._default = default

    @property
    def env_var(self) -> str:
        return self._env_var

    def load(self) -> SourceValueTV | Undefined:
        value = os.environ.get(self._env_var)
        if value is not None:
            return self._apply_converter(value)
        if self._default is not _undefined:
            return self._default
        return _undefined

    def __repr__(self) -> str:
        return f"EnvVarSource({self._env_var!r})"


class JsonFileSource(SettingSource[SourceValueTV]):
    """JSON file setting source.

    Supports nested keys using dot notation.

    Example
    -------
    >>> JsonFileSource("config.json", "database.host")
    >>> JsonFileSource("settings.json", "server.port", converter=int)
    """

    def __init__(
        self,
        file_path: str | Path,
        key: str,
        package: Opt[str] = None,
        priority: int = 50,
        converter: Opt[typing.Callable[[typing.Any], SourceValueTV]] = None,
    ):
        """
        Parameters
        ----------
        file_path : str | Path
            Path to the JSON file.
        key : str
            Key to look up in the JSON. Supports dot notation for nested keys.
        package : str | None
            Package name for loading packaged resources.
        priority : int
            Source priority. Default is 50.
        converter : Callable | None
            Optional value converter.
        """
        super().__init__(priority=priority, converter=converter)
        self._file_path = str(file_path)
        self._key = key
        self._package = package

    @property
    def file_path(self) -> str:
        return self._file_path

    @property
    def key(self) -> str:
        return self._key

    def load(self) -> SourceValueTV | Undefined:
        try:
            data = load_json_file(self._file_path, package=self._package)
            if not data:
                return _undefined

            value = get_nested_value(data, self._key)
            if value is None:
                return _undefined

            return self._apply_converter(value)
        except Exception:
            return _undefined

    def __repr__(self) -> str:
        return f"JsonFileSource({self._file_path!r}, {self._key!r})"


class PythonSource(SettingSource[SourceValueTV]):
    """Python module/object setting source.

    Loads a value from a Python module's attribute.

    Example
    -------
    >>> PythonSource("myapp.config", "DATABASE_URL")
    >>> PythonSource("myapp.settings", "Config.debug")
    """

    def __init__(
        self,
        module_path: str,
        attr_path: str,
        priority: int = 50,
        converter: Opt[typing.Callable[[typing.Any], SourceValueTV]] = None,
    ):
        """
        Parameters
        ----------
        module_path : str
            Dotted path to the Python module.
        attr_path : str
            Attribute path within the module. Supports dot notation.
        priority : int
            Source priority. Default is 50.
        converter : Callable | None
            Optional value converter.
        """
        super().__init__(priority=priority, converter=converter)
        self._module_path = module_path
        self._attr_path = attr_path

    @property
    def module_path(self) -> str:
        return self._module_path

    @property
    def attr_path(self) -> str:
        return self._attr_path

    def load(self) -> SourceValueTV | Undefined:
        try:
            module = __import__(
                self._module_path, fromlist=[self._attr_path.split(".")[0]]
            )
            value = module
            for attr in self._attr_path.split("."):
                value = getattr(value, attr)
            return self._apply_converter(value)
        except (ImportError, AttributeError):
            return _undefined

    def __repr__(self) -> str:
        return f"PythonSource({self._module_path!r}, {self._attr_path!r})"
