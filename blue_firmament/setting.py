"""BlueFirmament Setting Module

"""

__all__ = [
    "Setting",
    "EnvSetting", 
    "JsonFileSetting",
    "EnvJsonSetting",
    "PythonScriptSetting",
    "make_setting_singleton",
    "private_field", "field",
]

import os
import pkg_resources
import typing
from typing import Optional as Opt, Annotated as Anno, Literal as Lit
from .scheme.field import get_default
from .scheme import FieldT, field, private_field, BaseScheme
from .utils.file import load_json_file
from . import __name__ as PACKAGE_NAME


class Setting(BaseScheme,
    proxy=False,
):

    """Setting base class.
    """
    
    _setting_name: FieldT[str] = private_field()
    """配置名称"""
    _setting_path: FieldT[str | None] = private_field(default=None)
    """
    配置文件路径
    
    如果是打包在包内的配置文件，使用相对路径（不要用slash开头） \n
    如果是可以基于当前工作目录的配置文件，使用`./`或不使用任何前缀开头

    Example
    ^^^^^^^
    - ``./config.json``: 相对于CWD
    - ``data/config.json``: 相对于包
    - ``data/config/base``: 相对于包（目录）
    """
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

        """
        获取被打包/未打包的资源的路径（免去判断资源是否被打包）

        :param file_path: str
            相对于该包的资源路径
        """
        if get_default(cls._is_packaged):
            return pkg_resources.resource_filename(
                get_default(cls._package_name),
                file_path
            )

        return file_path
    
    @property
    def setting_path(self):

        '''配置文件路径

        如果没有配置（None），直接返回 \n
        如果是打包在包内的配置文件，返回绝对路径 \n
        '''

        if self._setting_path is None:
            return None
        return self.get_resource_path(self._setting_path)

    @classmethod
    def load(cls) -> typing.Self:
        return cls()


class EnvSetting(Setting,
    partial=True
):

    """Load setting by environment.

    Kinds of environments:
    - base
    - local
    - your customized env, like production, development...

    Guidance
    --------
    Your base env setting class should inherit this class.
    And then define what field does this setting has in the base
    env setting class.

    Add more env like production, development or local (built-in) setting
    by inheriting your base env setting class. (This will ensure field's type
    safety)
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
        
        return typing.cast(typing.Self, 
            base_cls(**env_cls(**local_cls()))
        )


class JsonFileSetting(Setting):

    """
    JSON文件配置
    """

    @classmethod
    def load(cls) -> typing.Self:

        # 仍然需要使用 field_as_class_var，因为此时数据模型没有被实例化
        fp = get_default(cls._setting_path)
        if fp:
            data = load_json_file(cls.get_resource_path(fp))
            try:
                return cls(**data)
            except ValueError as e:
                from .log.main import get_logger
                logger = get_logger(__name__)
                logger.error(f"Validation error in JsonSettingLoader {get_default(cls._setting_path)}: {e}")
                raise e
        else:
            raise ValueError("Setting path is not set")

class EnvJsonSetting(Setting):
    
    """
    多环境JSON配置
    """

    _setting_env: FieldT[str] = private_field(default_factory=lambda: os.environ.get("ENV", "production"))
    """配置环境"""

    @classmethod
    def load(cls) -> typing.Self:

        """
        加载多环境JSON配置文件

        顺序（优先级从低到高）：
        - .base.json
        - .{env}.json
        - .local.json

        可能抛出的错误：
        - ValidationError: 配置文件不符合数据模型定义
        """
        from .log.main import get_logger
        logger = get_logger(__name__)
        
        setting_name = get_default(cls._setting_name)
        setting_path = get_default(cls._setting_path)
        setting_env = get_default(cls._setting_env)
        package_name = get_default(cls._package_name) if get_default(cls._is_packaged) else None

        logger.debug(f"Loading setting {setting_name} in {setting_env} environment")

        data = {}
        data.update(load_json_file(f"{setting_path}/{setting_name}.base.json", package=package_name))
        data.update(load_json_file(f"{setting_path}/{setting_name}.{setting_env}.json", package=package_name))
        data.update(load_json_file(f"{setting_path}/{setting_name}.local.json", package=package_name))

        try:
            return cls(**data)
        except ValueError as e:
            from .log.main import get_logger
            logger = get_logger(__name__)
            logger.error(f"Validation error in {get_default(cls._setting_name)} EnvJsonSetting loader: {e}")
            raise e

class PythonScriptSetting(Setting):

    """
    Python脚本配置

    加载py脚本中的setting字段作为设置，该字段为可索引对象
    """

    def __init__(self):
        
        from .log.main import get_logger
        logger = get_logger(__name__)
        logger.debug(f"Loading python script setting: {self._setting_path}")

        py_setting = __import__(
            name=self._setting_name, fromlist=["setting"]
        ).setting
        super().__init__(**py_setting)


ClsType = typing.TypeVar("ClsType", bound=Setting)
def make_setting_singleton(
    cls_ins: ClsType
) -> typing.Tuple[typing.Callable[[], ClsType], typing.Callable[[ClsType], None]]:
    
    """使用单例模式来获取配置实例
    
    该函数返回两个函数：一个用于获取配置实例，一个用于设置配置实例

    Example
    ^^^^^^^

    .. code-block:: python
        from blue_firmament.setting import make_setting_singleton, Setting

        class MySetting(Setting):

            _setting_name = "my_setting"
            some_setting_field: str = 'a'
        
        get_setting, set_setting = make_setting_singleton(MySetting())
    """

    _setting_ins = cls_ins

    def get_setting():
        return _setting_ins
    
    def set_setting(setting: ClsType):
        nonlocal _setting_ins
        _setting_ins = setting

    return get_setting, set_setting