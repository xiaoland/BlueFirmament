
from ...setting import Setting, make_setting_singleton
from ...model import private_field, Field

class BaseSetting(Setting):

    _setting_name: Field[str] = private_field(default="base")

    timezone_delta: int = 8
    '''时区偏移量（相较于UTC+0时区）'''


get_setting, set_setting = make_setting_singleton(BaseSetting())
