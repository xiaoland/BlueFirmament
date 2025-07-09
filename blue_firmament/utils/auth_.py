"""Utils for Authorization."""

__all__ = [
    "decode_jwt",
    "decode_token"
]

import jwt
import typing
from typing import Annotated as Anno, Optional as Opt, Literal as Lit
from ..data.settings.auth import get_setting as get_auth_setting
from ..exceptions import ParamsInvalid


class JWTPayload(typing.TypedDict):
    sub: str
    """Subject"""
    iss: str
    """Issuer"""
    iat: int
    """Issued at (Unix timestamp in seconds)"""
    exp: int
    """Expiration time (Unix timestamp in seconds)"""
    roles: typing.Iterable[str]
    """Roles of the subject"""
    sid: str
    """Session ID"""

def decode_jwt(
    token: str,
    key: str,
    algorithms: typing.Iterable[str] = ("HS256",),
    audience: typing.Iterable[str] = ()
) -> JWTPayload:
    try:
        return JWTPayload(**jwt.decode(
            jwt=token,
            key=key,
            algorithms=algorithms,
            audience=audience
        ))
    except jwt.exceptions.InvalidSignatureError:
        raise ParamsInvalid(
            'JWT signature invalid',
            token=token, key=key,
        )
    except jwt.exceptions.DecodeError:
        raise ParamsInvalid(
            'JWT decode failed',
            token=token, algorithm=algorithms,
        )


def decode_token(token: str, token_type: Lit["jwt"] | str) -> dict | JWTPayload:
    if token_type == "jwt":
        return decode_jwt(
            token=token,
            key=get_auth_setting().jwt_secret_key,
            algorithms=get_auth_setting().jwt_algorithms,
            audience=get_auth_setting().jwt_allowed_audiences
        )
    else:
        raise ParamsInvalid(f"Unsupported token type: {token_type}")
