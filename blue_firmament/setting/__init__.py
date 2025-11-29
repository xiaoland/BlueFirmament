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
]

from .base import Setting, make_setting_singleton
from .field import SettingField, setting_field
from .source import (
    SettingSource,
    InlineSource,
    EnvVarSource,
    JsonFileSource,
    PythonSource,
)
