import datetime
import typing

from ...utils.datetime_ import get_datetimez
from ...setting import Setting, SettingField, InlineSource, make_setting_singleton

AuthSessionField = typing.Literal[
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

class AuthSetting(Setting):

    jwt_secret_key: SettingField[str] = SettingField(
        sources=[InlineSource("")],
        description="JWT secret key for signing tokens"
    )
    jwt_algorithms: SettingField[tuple[str, ...]] = SettingField(
        sources=[InlineSource(("HS256",))],
        description="JWT algorithms to use"
    )
    jwt_allowed_audiences: SettingField[tuple[str, ...]] = SettingField(
        sources=[InlineSource(())],
        description="JWT allowed audiences"
    )
    session_fields_getter: SettingField[dict[AuthSessionField, typing.Callable[[dict], typing.Any]]] = SettingField(
        sources=[InlineSource(SESSION_FIELDS_GETTER_DEFAULT)],
        description="Functions to extract session fields from JWT payload"
    )


get_setting, set_setting = make_setting_singleton(AuthSetting.load())
