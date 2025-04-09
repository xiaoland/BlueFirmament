"""
碧霄配置模块

该模块提供了一个统一的配置加载器，支持从JSON文件、Python脚本等多种方式加载配置，支持多环境配置和本地配置的覆盖。

Metadata
^^^^^^^^
- Authors:
    - Lan_zhijiang lanzhijiang@foxmail.com


Documentation
^^^^^^^^^^^^^
"""

import os
import pkg_resources
import typing

from .scheme.field import field_as_class_var
from .scheme.field import PrivateField
from .utils.file import load_json_file
from .scheme import BaseScheme, Field
from .utils.importer import import_modules
from typing import Optional
from . import __name__ as PACKAGE_NAME
import structlog

logger = structlog.get_logger(__name__)


class Setting(BaseScheme):

    """
    配置
    """
    
    _setting_name: str = PrivateField()
    """配置名称"""
    _setting_path: str | None = PrivateField(None)
    """
    配置文件路径
    
    如果是打包在包内的配置文件，使用相对路径（不要用slash开头） \n
    如果是可以基于当前工作目录的配置文件，使用`./`或不使用任何前缀开头
    """
    _is_packaged: bool = PrivateField(True)
    """是否打包在包内"""
    _package_name: str = PrivateField(PACKAGE_NAME)
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
        if field_as_class_var(cls._is_packaged):
            return pkg_resources.resource_filename(
                field_as_class_var(cls._package_name),
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


class JsonFileSetting(Setting):

    """
    JSON文件配置
    """

    def __init__(self):

        # 仍然需要使用 field_as_class_var，因为此时数据模型没有被实例化
        fp = field_as_class_var(self._setting_path)
        if fp:
            data = load_json_file(self.get_resource_path(fp))
            try:
                return super().__init__(**data)
            except ValueError as e:
                logger.error(f"Validation error in JsonSettingLoader {field_as_class_var(self._setting_path)}: {e}")
                raise e
        else:
            raise ValueError("Setting path is not set")

class EnvJsonSetting(Setting):
    
    """
    多环境JSON配置
    """

    _setting_env: Optional[str] = PrivateField(default_factory=lambda: os.environ.get("ENV", "production"))
    """配置环境"""

    def __init__(self):

        """
        加载多环境JSON配置文件

        顺序（优先级从低到高）：
        - .base.json
        - .{env}.json
        - .local.json

        可能抛出的错误：
        - ValidationError: 配置文件不符合数据模型定义
        """
        setting_name = field_as_class_var(self._setting_name)
        setting_path = field_as_class_var(self._setting_path)
        setting_env = field_as_class_var(self._setting_env)
        package_name = field_as_class_var(self._package_name) if field_as_class_var(self._is_packaged) else None

        logger.debug(f"Loading setting {setting_name} in {setting_env} environment")

        data = {}
        data.update(load_json_file(f"{setting_path}/{setting_name}.base.json", package=package_name))
        data.update(load_json_file(f"{setting_path}/{setting_name}.{setting_env}.json", package=package_name))
        data.update(load_json_file(f"{setting_path}/{setting_name}.local.json", package=package_name))

        try:
            return super().__init__(**data)
        except ValueError as e:
            logger.error(f"Validation error in {field_as_class_var(self._setting_name)} EnvJsonSetting loader: {e}")
            raise e

class PythonScriptSetting(Setting):

    """
    Python脚本配置

    加载py脚本中的setting字段作为设置，该字段为可索引对象
    """

    def __init__(self):

        logger.debug(f"Loading python script setting: {field_as_class_var(self._setting_path)}")

        py_setting = __import__(
            name=field_as_class_var(self._setting_name), fromlist=["setting"]
        ).setting
        super().__init__(**py_setting)


ClsType = typing.TypeVar("ClsType", bound=Setting)
def make_setting_singleton(
    cls_ins: ClsType
) -> typing.Tuple[typing.Callable[[], ClsType], typing.Callable[[ClsType], None]]:
    
    '''使用单例模式来获取配置实例
    
    该函数返回两个函数：一个用于获取配置实例，一个用于设置配置实例

    Example
    ^^^^^^^
    ```python
    from blue_firmament.setting import make_setting_singleton, Setting

    class MySetting(Setting):
    
        _setting_name = "my_setting"
        some_setting_field: str = 'a'

    
    get_setting, set_setting = make_setting_singleton(MySetting())
    '''

    _setting_ins = cls_ins

    def get_setting():
        return _setting_ins
    
    def set_setting(setting: ClsType):
        nonlocal _setting_ins
        _setting_ins = setting

    return get_setting, set_setting