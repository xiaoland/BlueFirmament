"""Legacy Setting Classes Module (Deprecated)

These classes are deprecated and kept for backward compatibility.
Use the new Setting class with SettingField and SettingSource instead.
"""

__all__ = [
    "EnvSetting",
    "JsonFileSetting",
    "EnvJsonSetting",
    "PythonScriptSetting",
]

import os
import typing

import pkg_resources

from ..model import BaseModel
from ..model.field import Field, get_default, private_field
from ..utils.file import load_json_file
from .. import __name__ as PACKAGE_NAME


class _LegacySetting(BaseModel, proxy=False):
    """Legacy Setting base class (deprecated).

    Use the new Setting class with SettingField and SettingSource instead.
    """

    _setting_name: Field[str] = private_field()
    """配置名称"""
    _setting_path: Field[str | None] = private_field(default=None)
    """配置文件路径"""
    _is_packaged: Field[bool] = private_field(default=True)
    """是否打包在包内"""
    _package_name: Field[str] = private_field(default=PACKAGE_NAME)
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

    __env_cls__: typing.Optional[typing.List[typing.Type["EnvSetting"]]] = None

    def __init_subclass__(cls) -> None:
        if not cls.__env_cls__:
            cls.__env_cls__ = []
        cls.__env_cls__.append(cls)

    _env: Field[str] = private_field()

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
                from ..log.main import get_logger

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

    _setting_env: Field[str] = private_field(
        default_factory=lambda: os.environ.get("ENV", "production")
    )

    @classmethod
    def load(cls) -> typing.Self:
        from ..log.main import get_logger

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
            from ..log.main import get_logger

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
        from ..log.main import get_logger

        logger = get_logger(__name__)
        logger.debug(f"Loading python script setting: {self._setting_path}")

        py_setting = __import__(name=self._setting_name, fromlist=["setting"]).setting
        super().__init__(**py_setting)
