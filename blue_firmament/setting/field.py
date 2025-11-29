"""Setting Field Module

SettingField class that loads values from multiple sources.
"""

__all__ = [
    "SettingField",
    "setting_field",
]

import typing
from typing import Optional as Opt

from ..model.field import Field, FieldValueTV
from ..model.converter import BaseConverter
from .._types import Undefined, _undefined
from .source import SettingSource

if typing.TYPE_CHECKING:
    from ..model.validator import BaseValidator
    from ..model.main import BaseModel


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
        scheme_cls: Opt[typing.Type["BaseModel"]] = None,
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
