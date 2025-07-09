"""Common Session and its fields
"""

import typing
from typing import Annotated as Anno, Optional as Opt, Literal as Lit
from ..exceptions import ParamsInvalid
from ..utils import auth_
from .. import event
from ..auth import AuthSession
from ..dal.base import DataAccessObjects
from . import Session, SessionField
from ..log.main import get_logger
LOGGER = get_logger(__name__)


class AuthSessionField(SessionField[AuthSession]):

    def __init__(
        self,
        access_token: str,
        access_token_type: str,
        access_token_payload: dict,
        refresh_token: Opt[str] = None
    ):
        super().__init__(AuthSession.from_token(
            access_token=access_token,
            access_token_type=access_token_type,
            access_token_payload=access_token_payload,
            refresh_token=refresh_token
        ))

    def is_expired(self) -> bool:
        return self.value.is_expired()

    def refresh(self) -> None:
        self.value.refresh()

class DAOsField(SessionField[DataAccessObjects]):

    def __init__(self, auth_session: AuthSession | AuthSessionField):
        if isinstance(auth_session, AuthSessionField):
            auth_session = auth_session.value
        super().__init__(DataAccessObjects(auth_session))

    def is_expired(self) -> bool:
        return self.value.is_expired()


class CommonSession(Session):
    """BlueFirmament Common Session

    Configure by setting class variables.
    """

    ACCESS_TOKEN_TYPE = "jwt"
    ACCESS_TOKEN_PAYLOAD_ID_CLAIM = "sid"
    """which claim in access token payload will be used as session id.
    """
    __fields__ = ("auth_session", "daos")

    def __init_fields__(
        self,
        daos: SessionField[DataAccessObjects],
        auth_session: SessionField[AuthSession],
    ) -> None:
        self.__daos = daos
        self.__auth_session = auth_session

    @property
    def daos(self):
        """DataAccessObjects
        """
        return self.__daos.value

    @property
    def operator(self):
        return self.__auth_session.value.user

    @classmethod
    def from_task(cls, task) -> typing.Self:
        authorization = task.metadata.authorization
        if authorization:
            access_token = authorization[1]
        else:
            raise ParamsInvalid('authorization not found in metadata')
        refresh_token = task.metadata.state.get("refresh_token", None)

        access_token_payload = auth_.decode_token(access_token, cls.ACCESS_TOKEN_TYPE)

        def get_fields():
            fields = {}
            fields["auth_session"] = AuthSessionField(
                access_token=access_token,
                access_token_type=cls.ACCESS_TOKEN_TYPE,
                access_token_payload=access_token_payload,
                refresh_token=refresh_token
            )
            fields["daos"] = DAOsField(fields["auth_session"])
            return fields

        return cls.upsert(
            access_token_payload[cls.ACCESS_TOKEN_PAYLOAD_ID_CLAIM],
            fields_getter=get_fields
        )
