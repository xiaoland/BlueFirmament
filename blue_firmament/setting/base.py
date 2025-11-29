"""Setting Base Module

Setting base class and singleton helper.
"""

__all__ = [
    "Setting",
    "make_setting_singleton",
    "ClsType",
]

import typing

from ..model import BaseModel
from .._types import _undefined
from .field import SettingField


class Setting(
    BaseModel,
    proxy=False,
    partial=True,
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
