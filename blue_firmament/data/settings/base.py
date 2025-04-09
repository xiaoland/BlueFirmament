
from ...setting import Setting, make_setting_singleton

class BaseSetting(Setting):

    _setting_name: str = "base"

    timezone_delta: int = 8
    '''时区偏移量（相较于UTC+0时区）'''

    session_expire_time: int = 300
    '''会话过期时间（单位：秒）'''


get_setting, set_setting = make_setting_singleton(BaseSetting())
