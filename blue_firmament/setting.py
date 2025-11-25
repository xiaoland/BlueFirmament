"""BlueFirmament Setting Module

Setting is a dataclass (based on BlueFirmament.BaseScheme), every field must be SettingField.
A SettingField has a list of SettingSource to load field value from, like JsonFileSource,
EnvVarSource, PythonSource, InlineSource.

Example
-------
.. code-block:: python

    from blue_firmament.setting import (
        Setting, SettingField,
        EnvVarSource, JsonFileSource, InlineSource
    )

    class MySetting(Setting):
        database_url: SettingField[str] = SettingField(
            sources=[
                EnvVarSource("DATABASE_URL"),
                JsonFileSource("config.json", "database.url"),
                InlineSource("sqlite:///default.db")
            ]
        )

        debug: SettingField[bool] = SettingField(
            sources=[
                EnvVarSource("DEBUG", converter=lambda x: x.lower() == "true"),
                InlineSource(False)
            ]
        )

    setting = MySetting.load()
"""

__all__ = [
    # Setting base
    "Setting",
    "make_setting_singleton",
    # Setting Field
    "SettingField",
    "setting_field",
    # Setting Sources
    "SettingSource",
    "InlineSource",
    "EnvVarSource",
    "JsonFileSource",
    "PythonSource",
    # Deprecated (for backward compatibility)
    "EnvSetting",
    "JsonFileSetting",
    "EnvJsonSetting",
    "PythonScriptSetting",
    "private_field",
    "field",
]

import abc
import os
import json
import typing
from pathlib import Path
from typing import Optional as Opt

from .model.field import Field, get_default, private_field, FieldValueTV
from .model import FieldT, field, private_field, BaseScheme
from .model.converter import BaseConverter, get_converter_from_anno
from .utils.file import load_json_file
from .utils.dict_ import get_nested_value
from ._types import Undefined, _undefined

if typing.TYPE_CHECKING:
    from .model.validator import BaseValidator


# =============================================================================
# Setting Sources
# =============================================================================

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


# =============================================================================
# Setting Field
# =============================================================================


class SettingField(Field[FieldValueTV]):
    """A field for settings that loads its value from multiple sources.

    Sources are tried in priority order (highest first) until one returns a value.

    Example
    -------
    >>> class MySetting(Setting):
    ...     port: SettingField[int] = SettingField(
    ...         sources=[
    ...             EnvVarSource("PORT", converter=int),
    ...             JsonFileSource("config.json", "server.port"),
    ...             InlineSource(8080)
    ...         ]
    ...     )
    """

    def __init__(
        self,
        sources: Opt[typing.List[SettingSource[FieldValueTV]]] = None,
        default: typing.Union[Undefined, FieldValueTV] = _undefined,
        default_factory: Opt[typing.Callable[[], FieldValueTV]] = None,
        vtype: Undefined | typing.Type[FieldValueTV] = _undefined,
        name: Opt[str] = None,
        in_scheme_name: Opt[str] = None,
        converter: Opt[BaseConverter[FieldValueTV]] = None,
        validators: Opt[typing.Iterable["BaseValidator"]] = None,
        description: Opt[str] = None,
    ):
        """
        Parameters
        ----------
        sources : List[SettingSource] | None
            List of sources to load the value from. Tried in priority order.
        default : FieldValueTV | Undefined
            Default value if no source provides a value.
        default_factory : Callable[[], FieldValueTV] | None
            Factory for mutable default values.
        vtype : Type[FieldValueTV] | Undefined
            Value type hint.
        name : str | None
            Field name.
        in_scheme_name : str | None
            Field name in scheme.
        converter : BaseConverter | None
            Value converter.
        validators : Iterable[BaseValidator] | None
            Field validators.
        description : str | None
            Human-readable description of this setting.
        """
        super().__init__(
            default=default,
            default_factory=default_factory,
            vtype=vtype,
            name=name,
            in_scheme_name=in_scheme_name,
            converter=converter,
            validators=validators,
            is_partial=True,  # Settings are partial by default
            init=True,
        )
        self._sources: typing.List[SettingSource[FieldValueTV]] = sources or []
        self._description = description
        # Sort sources by priority (highest first)
        self._sources.sort(key=lambda s: s.priority, reverse=True)

    @property
    def sources(self) -> typing.List[SettingSource[FieldValueTV]]:
        return self._sources

    @property
    def description(self) -> Opt[str]:
        return self._description

    def add_source(self, source: SettingSource[FieldValueTV]) -> None:
        """Add a source and re-sort by priority."""
        self._sources.append(source)
        self._sources.sort(key=lambda s: s.priority, reverse=True)

    def load_from_sources(self) -> FieldValueTV | Undefined:
        """Load value from sources in priority order.

        Returns
        -------
        FieldValueTV | Undefined
            The first successfully loaded value, or _undefined if no source provides a value.
        """
        for source in self._sources:
            value = source.load()
            if value is not _undefined:
                return value
        return _undefined

    def fork(
        self,
        sources: Opt[typing.List[SettingSource[FieldValueTV]]] = None,
        default: Undefined | FieldValueTV = _undefined,
        default_factory: Opt[typing.Callable[[], FieldValueTV]] = None,
        vtype: Undefined | typing.Type[FieldValueTV] = _undefined,
        name: Opt[str] = None,
        in_scheme_name: Opt[str] = None,
        scheme_cls: Opt[typing.Type["BaseScheme"]] = None,
        converter: Opt[BaseConverter[FieldValueTV]] = None,
        fork_validators: bool = False,
        description: Opt[str] = None,
        **kwargs,  # Accept additional kwargs for compatibility with parent
    ) -> typing.Self:
        """Create a copy of this field with overridden values."""
        forked = super().fork(
            default=default,
            default_factory=default_factory,
            vtype=vtype,
            name=name,
            in_scheme_name=in_scheme_name,
            scheme_cls=scheme_cls,
            converter=converter,
            fork_validators=fork_validators,
            is_partial=True,
            **kwargs,
        )
        # SettingField-specific attributes
        forked._sources = sources if sources is not None else self._sources.copy()
        forked._description = (
            description if description is not None else self._description
        )
        return forked

    def dump_val_to_jsonable(self, value: FieldValueTV) -> typing.Any:
        """Dump field value to jsonable types.

        For SettingField, we handle values even without a converter defined,
        since settings often have simple types that are already jsonable.
        """
        if value is _undefined:
            return _undefined.value

        # Try to use converter if available
        try:
            return self.converter.dump_to_jsonable(value)
        except ValueError:
            # No converter, return value as-is (works for simple types)
            return value

    def __repr__(self) -> str:
        return f"SettingField(sources={self._sources!r})"


def setting_field(
    sources: Opt[typing.List[SettingSource[FieldValueTV]]] = None,
    default: FieldValueTV | Undefined = _undefined,
    default_factory: Opt[typing.Callable[[], FieldValueTV]] = None,
    name: Opt[str] = None,
    converter: Opt[BaseConverter[FieldValueTV]] = None,
    validators: Opt[typing.Iterable["BaseValidator"]] = None,
    description: Opt[str] = None,
) -> SettingField[FieldValueTV]:
    """Factory function for creating SettingField instances.

    Example
    -------
    >>> class MySetting(Setting):
    ...     port: int = setting_field(
    ...         sources=[EnvVarSource("PORT", converter=int)],
    ...         default=8080
    ...     )
    """
    return SettingField(
        sources=sources,
        default=default,
        default_factory=default_factory,
        name=name,
        converter=converter,
        validators=validators,
        description=description,
    )


# =============================================================================
# Setting Base Class
# =============================================================================

if typing.TYPE_CHECKING:
    from .model.main import BaseScheme


class Setting(
    BaseScheme,
    proxy=False,
    partial=True,
    disable_log=True,
):
    """Setting base class.

    Settings are dataclasses that load their field values from multiple sources.
    Each field should be a SettingField with a list of SettingSource instances.

    Example
    -------
    >>> class AppSetting(Setting):
    ...     database_url: SettingField[str] = SettingField(
    ...         sources=[
    ...             EnvVarSource("DATABASE_URL"),
    ...             JsonFileSource("config.json", "database.url"),
    ...             InlineSource("sqlite:///default.db")
    ...         ],
    ...         description="Database connection URL"
    ...     )
    ...
    >>> setting = AppSetting.load()
    >>> print(setting.database_url)
    """

    @classmethod
    def load(cls) -> typing.Self:
        """Load setting by resolving all SettingField sources.

        For each SettingField, tries sources in priority order until
        one provides a value.

        Returns
        -------
        Self
            An instance of this Setting class with all fields populated.
        """
        data: typing.Dict[str, typing.Any] = {}

        # Collect all fields (including inherited)
        all_fields = {**cls.__fields__, **cls.__private_fields__}

        for field_name, field_ins in all_fields.items():
            if isinstance(field_ins, SettingField):
                value = field_ins.load_from_sources()
                if value is not _undefined:
                    data[field_name] = value
            # For non-SettingField fields, use default behavior

        return cls(**data)

    def reload(self) -> None:
        """Reload setting values from sources.

        Updates this instance in-place with fresh values from sources.
        """
        all_fields = {**self.__fields__, **self.__private_fields__}

        for field_name, field_ins in all_fields.items():
            if isinstance(field_ins, SettingField):
                value = field_ins.load_from_sources()
                if value is not _undefined:
                    setattr(self, field_name, value)


# =============================================================================
# Singleton Helper
# =============================================================================

ClsType = typing.TypeVar("ClsType", bound=Setting)


def make_setting_singleton(
    cls_ins: ClsType,
) -> typing.Tuple[typing.Callable[[], ClsType], typing.Callable[[ClsType], None]]:
    """Create a singleton pattern for a setting instance.

    Returns two functions: one to get the setting instance, one to set it.

    Example
    -------
    .. code-block:: python

        from blue_firmament.setting import make_setting_singleton, Setting, SettingField, InlineSource

        class MySetting(Setting):
            some_field: SettingField[str] = SettingField(
                sources=[InlineSource("default")]
            )

        get_setting, set_setting = make_setting_singleton(MySetting.load())

        # Usage
        setting = get_setting()
        print(setting.some_field)
    """
    _setting_ins = cls_ins

    def get_setting() -> ClsType:
        return _setting_ins

    def set_setting(setting: ClsType) -> None:
        nonlocal _setting_ins
        _setting_ins = setting

    return get_setting, set_setting


# =============================================================================
# Deprecated Classes (for backward compatibility)
# =============================================================================

import pkg_resources
from . import __name__ as PACKAGE_NAME


class _LegacySetting(BaseScheme, proxy=False, disable_log=True):
    """Legacy Setting base class (deprecated).

    Use the new Setting class with SettingField and SettingSource instead.
    """

    _setting_name: FieldT[str] = private_field()
    """配置名称"""
    _setting_path: FieldT[str | None] = private_field(default=None)
    """配置文件路径"""
    _is_packaged: FieldT[bool] = private_field(default=True)
    """是否打包在包内"""
    _package_name: FieldT[str] = private_field(default=PACKAGE_NAME)
    """所属包的包名"""

    @property
    def is_packaged(self):
        return self._is_packaged

    @property
    def package_name(self):
        return self._package_name

    @classmethod
    def get_resource_path(cls, file_path: str) -> str:
        if get_default(cls._is_packaged):
            return pkg_resources.resource_filename(
                get_default(cls._package_name), file_path
            )
        return file_path

    @property
    def setting_path(self):
        if self._setting_path is None:
            return None
        return self.get_resource_path(self._setting_path)

    @classmethod
    def load(cls) -> typing.Self:
        return cls()


class EnvSetting(_LegacySetting, partial=True):
    """Load setting by environment (deprecated).

    Use the new Setting class with EnvVarSource instead.
    """

    __env_cls__: Opt[typing.List[typing.Type["EnvSetting"]]] = None

    def __init_subclass__(cls) -> None:
        if not cls.__env_cls__:
            cls.__env_cls__ = []
        cls.__env_cls__.append(cls)

    _env: FieldT[str] = private_field()

    @classmethod
    def __find_env_cls(cls, env_name: str) -> typing.Type["EnvSetting"]:
        if not cls.__env_cls__:
            raise ValueError("no env cls registered")
        for i in cls.__env_cls__:
            if get_default(i._env) == env_name:
                return i
        raise ValueError(f"env {env_name} setting not found")

    @classmethod
    def load(cls) -> typing.Self:
        base_cls = cls.__find_env_cls("base")
        local_cls = cls.__find_env_cls("local")
        env_cls = cls.__find_env_cls(os.environ.get("ENV", "production"))

        return typing.cast(typing.Self, base_cls(**env_cls(**local_cls())))


class JsonFileSetting(_LegacySetting):
    """JSON文件配置 (deprecated).

    Use the new Setting class with JsonFileSource instead.
    """

    @classmethod
    def load(cls) -> typing.Self:
        fp = get_default(cls._setting_path)
        if fp:
            data = load_json_file(cls.get_resource_path(fp))
            try:
                return cls(**data)
            except ValueError as e:
                from .log.main import get_logger

                logger = get_logger(__name__)
                logger.error(
                    f"Validation error in JsonSettingLoader {get_default(cls._setting_path)}: {e}"
                )
                raise e
        else:
            raise ValueError("Setting path is not set")


class EnvJsonSetting(_LegacySetting, partial=True):
    """多环境JSON配置 (deprecated).

    Use the new Setting class with JsonFileSource and EnvVarSource instead.
    """

    _setting_env: FieldT[str] = private_field(
        default_factory=lambda: os.environ.get("ENV", "production")
    )

    @classmethod
    def load(cls) -> typing.Self:
        from .log.main import get_logger

        logger = get_logger(__name__)

        setting_name = get_default(cls._setting_name)
        setting_path = get_default(cls._setting_path)
        setting_env = get_default(cls._setting_env)
        package_name = (
            get_default(cls._package_name) if get_default(cls._is_packaged) else None
        )

        logger.debug(f"Loading setting {setting_name} in {setting_env} environment")

        data = {}
        data.update(
            load_json_file(
                f"{setting_path}/{setting_name}.base.json", package=package_name
            )
        )
        data.update(
            load_json_file(
                f"{setting_path}/{setting_name}.{setting_env}.json",
                package=package_name,
            )
        )
        data.update(
            load_json_file(
                f"{setting_path}/{setting_name}.local.json", package=package_name
            )
        )

        try:
            return cls(**data)
        except ValueError as e:
            from .log.main import get_logger

            logger = get_logger(__name__)
            logger.error(
                f"Validation error in {get_default(cls._setting_name)} EnvJsonSetting loader: {e}"
            )
            raise e


class PythonScriptSetting(_LegacySetting):
    """Python脚本配置 (deprecated).

    Use the new Setting class with PythonSource instead.
    """

    def __init__(self):
        from .log.main import get_logger

        logger = get_logger(__name__)
        logger.debug(f"Loading python script setting: {self._setting_path}")

        py_setting = __import__(name=self._setting_name, fromlist=["setting"]).setting
        super().__init__(**py_setting)
