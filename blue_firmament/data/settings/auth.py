import datetime
import typing

from ...utils.datetime_ import get_datetimez
from ...scheme import private_field
from ...setting import EnvJsonSetting, make_setting_singleton

type AuthSessionField = typing.Literal[
    "session_id",
    "user_id",
    "roles",
    "expire_at",
    "issued_at"
]
SESSION_FIELDS_GETTER_DEFAULT: dict[AuthSessionField, typing.Callable[[dict], typing.Any]] = {
    "session_id": lambda payload: payload["sid"],
    "expire_at": lambda payload: get_datetimez(timestamp=payload["exp"]),
    "issued_at": lambda payload: get_datetimez(timestamp=payload["iat"]),
    "user_id": lambda payload: payload["sub"],
    "roles": lambda payload: payload["roles"],
}

class AuthSetting(EnvJsonSetting):

    _setting_name = private_field(default="auth")
    _is_packaged = private_field(default=False)

    jwt_secret_key: str = ""
    jwt_algorithms: tuple[str, ...] = ("HS256",)
    jwt_allowed_audiences: tuple[str, ...] = ()
    session_fields_getter: dict[AuthSessionField, typing.Callable[[dict], typing.Any]] = \
        SESSION_FIELDS_GETTER_DEFAULT


get_setting, set_setting = make_setting_singleton(AuthSetting.load())
