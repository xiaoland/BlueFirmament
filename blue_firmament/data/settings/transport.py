
from ...setting import Setting, make_setting_singleton

class TransportSetting(Setting):

    _setting_name = "transport"
    
    jwt_secret_key: str | None = None
    jwt_algorithm: str = 'HS256'


get_setting, set_setting = make_setting_singleton(TransportSetting())
