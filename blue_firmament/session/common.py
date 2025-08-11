"""Common Session and its fields
"""

import typing
import uuid
from typing import Annotated as Anno, Optional as Opt, Literal as Lit

from ..exceptions import Unauthorized
from ..utils import auth_
from ..auth import AuthSession, User
from ..dal.base import DataAccessObjects
from . import Session, SessionField
from ..log.main import get_logger
LOGGER = get_logger(__name__)


class AuthSessionField(SessionField[AuthSession | None]):

    class FromToken(typing.TypedDict):
        access_token: str
        access_token_type: str
        access_token_payload: dict
        refresh_token: Opt[str]

    def __init__(
        self,
        from_token: Opt[FromToken] = None,
    ):
        if from_token:
            super().__init__(AuthSession.from_token(
                access_token=from_token["access_token"],
                access_token_type=from_token["access_token_type"],
                access_token_payload=from_token["access_token_payload"],
                refresh_token=from_token.get("refresh_token", None)
            ))
        else:
            super().__init__(None)

    def is_expired(self) -> bool:
        if self.value:
            return self.value.is_expired()
        return False

    def refresh(self) -> None:
        if self.value:
            self.value.refresh()

class DAOsField(SessionField[DataAccessObjects]):

    def __init__(self, auth_session: AuthSession | AuthSessionField | None = None):
        if isinstance(auth_session, AuthSessionField):
            super().__init__(DataAccessObjects(auth_session.value))
        else:
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
        auth_session: SessionField[AuthSession | None],
    ) -> None:
        self.__daos = daos
        self.__auth_session = auth_session

    @property
    def daos(self) -> DataAccessObjects:
        """DataAccessObjects
        """
        return self.__daos.value

    @property
    def operator(self) -> User:
        if self.__auth_session.value:
            return self.__auth_session.value.user
        raise Unauthorized("tries to access operator but unauthorized")

    @classmethod
    def from_task(cls, task) -> typing.Self:
        authorization = task.metadata.authorization
        if authorization:
            access_token = authorization[1]
        else:
            LOGGER.warning('authorization not found in metadata')
            access_token = None
        refresh_token = task.metadata.state.get("refresh_token", None)

        access_token_payload = {}
        if access_token:
            access_token_payload = auth_.decode_token(access_token, cls.ACCESS_TOKEN_TYPE)

        def get_fields():
            fields = {}
            if access_token and access_token_payload:
                fields["auth_session"] = AuthSessionField(
                    from_token=AuthSessionField.FromToken(
                        access_token=access_token,
                        access_token_type=cls.ACCESS_TOKEN_TYPE,
                        access_token_payload=access_token_payload,
                        refresh_token=refresh_token
                    )
                )
            else:
                fields["auth_session"] = AuthSessionField()
            fields["daos"] = DAOsField(fields["auth_session"])
            return fields

        return cls.upsert(
            access_token_payload.get(cls.ACCESS_TOKEN_PAYLOAD_ID_CLAIM, uuid.uuid4().hex),
            fields_getter=get_fields
        )
