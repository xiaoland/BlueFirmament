
import logging

from ...setting import Setting, make_setting_singleton


class LogSetting(Setting):

    _setting_name: str = "log"

    log_level: logging._Level = logging.INFO


get_setting, set_setting = make_setting_singleton(LogSetting())

