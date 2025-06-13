
from ...scheme import private_field
from ...setting import EnvJsonSetting, make_setting_singleton


class AuthSetting(EnvJsonSetting):

    _setting_name = private_field(default="auth")
    _is_packaged = private_field(default=False)

    jwt_secret_key: str = ""
    jwt_algorithm: str = ""
    supabase_auth_url: str = ""
    supabase_serv_key: str = ""
    supabase_anon_key: str = ""
    

get_setting, set_setting = make_setting_singleton(AuthSetting.load())
