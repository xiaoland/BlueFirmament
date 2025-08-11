"""Auth module
"""

__all__ = [
    "User",
    "AuthSession"
]

import abc
import datetime
import typing
from typing import Annotated as Anno, Optional as Opt, Literal as Lit

from .utils import auth_
from .utils.datetime_ import get_datetimez
from .utils.main import dump_iterable
from .data.settings.auth import get_setting as get_auth_setting
from .log import get_logger
LOGGER = get_logger(__name__)


class User(abc.ABC):

    def __init__(
        self,
        _id,
        roles: set[str]
    ):
        self.__id = _id
        self.__roles: set[str] = roles

    @property
    def id(self):
        """ID of the user.
        """
        return self.__id

    @property
    def roles(self):
        """Roles of the user.
        """
        return self.__roles

    def has_role(self, role: str) -> bool:
        return role in self.__roles


class AuthSession(abc.ABC):
    """Session of auth module.
    """

    def __init__(
        self,
        _id: str,
        access_token: str,
        user: User,
        refresh_token: Opt[str] = None,
        expire_at: Opt[datetime.datetime] = None,
    ) -> None:
        self.__id = _id
        self.__access_token = access_token
        self.__refresh_token = refresh_token
        self.__user = user
        self.__expire_at = expire_at

    @property
    def id(self):
        """Session ID"""
        return self.__id
    @property
    def user(self):
        """User of the session"""
        return self.__user
    @property
    def access_token(self):
        return self.__access_token

    def is_expired(self) -> bool:
        if self.__expire_at is None:
            return False
        return get_datetimez() > self.__expire_at

    def refresh(self) -> None:
        """Refresh the session with refresh token.

        :raise ParamsInvalid: if refresh token is not set.
        """
    
    @classmethod
    def from_token(
        cls,
        access_token: str,
        access_token_type: Lit["jwt"] | str = "jwt",
        access_token_payload: Opt[dict] = None,
        refresh_token: Opt[str] = None,
    ) -> typing.Self:
        """Init an AuthSession from an access token.

        :param access_token:
        :param access_token_type: JWT, etc.
            Defaults to "jwt".
        :param access_token_payload: When you already have the decoded the token.
        :param refresh_token:
        :return: An AuthSession instance.

        JsonWebToken
        ^^^^^^^^^^^^
        - Requires a JWT secret key and algorithm configured in
          :meth:`blue_firmament.data.setting.auth.AuthSetting`.
        - These setting are optional:
            - Allowed Audience
        - Payload claims maps to AuthSession fields, you can override
          by setting `jwt_claims_map` in AuthSetting.
            - `sid`: Session ID
            - `sub`: User ID
            - `roles`: User roles
        """
        if access_token_payload is None:
            access_token_payload = auth_.decode_token(access_token, access_token_type)

        return cls(
            access_token=access_token,
            refresh_token=refresh_token,
            **cls._normalize_token_payload(access_token_payload)
        )

    @staticmethod
    def _normalize_token_payload(payload: dict) -> dict:
        """Normalize access token payload to AuthSession fields.
        """
        getters = get_auth_setting().session_fields_getter
        return dict(
            _id=getters["session_id"](payload),
            expire_at=getters["expire_at"](payload),
            user=User(
                _id=getters["user_id"](payload),
                roles=dump_iterable(
                    set, getters["roles"](payload)
                )
            )
        )




