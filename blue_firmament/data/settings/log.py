
import logging
import typing
from typing import Optional as Opt, Annotated as Anno, Literal as Lit
from ...setting import Setting, make_setting_singleton
from ...scheme import private_field


class LogSetting(Setting):

    __disable_log__ = True

    _setting_name = private_field("log")
    
    log_level: int = logging.INFO
    log_file: Opt[str]  = None
    cache_logger_on_first_use: bool = False


get_setting, set_setting = make_setting_singleton(LogSetting())

