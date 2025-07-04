"""Common Session and its fields
"""

import typing
from .. import event
from ..auth import AuthSession, SupabaseAuthSession
from ..dal.base import DataAccessObjects
from . import Session, SessionField
from ..log.main import get_logger
LOGGER = get_logger(__name__)


class CommonSession(Session):

    def __init__(
        self, _id, /,
        daos: SessionField[DataAccessObjects],
        auth_session: SessionField[AuthSession],
    ) -> None:
        super().__init__(_id)
        self.__daos = daos
        self.__auth_session = auth_session

    @property
    def daos(self):
        return self.__daos.value
    @property
    def operator(self):
        return self.__auth_session.value.user
    @property
    def emit(self):
        return event.simple_emit

    @classmethod
    def from_task(cls, task) -> typing.Self:

        authorization = task.metadata.authorization
        jwt_str = None
        if not authorization:
            jwt_str = task.get_state_item("authorization")
            # FIXME put task.session ?
        else:
            jwt_str = authorization[1]

        if not jwt_str:
            LOGGER.warning('Cannot find valid JWT in headers or cookies')
            raise ValueError('JWT not found')
        
        auth_session = SessionField(SupabaseAuthSession.from_token(jwt_str))
        daos = SessionField(DataAccessObjects(auth_session.value))

        return cls.get_session(
            auth_session.value.id, 
            daos=daos,
            auth_session=auth_session,
        )
