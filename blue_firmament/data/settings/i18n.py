
from ...setting import Setting, make_setting_singleton


class I18NSetting(Setting):

    _setting_name = "i18n"

    


get_setting, set_setting = make_setting_singleton(I18NSetting())
