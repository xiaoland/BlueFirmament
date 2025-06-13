
from ...setting import Setting, make_setting_singleton
from ...scheme import private_field

class SessionSetting(Setting):

    _setting_name = private_field("session")
    
    jwt_secret_key: str | None = None
    jwt_algorithm: str = 'HS256'


get_setting, set_setting = make_setting_singleton(SessionSetting())
