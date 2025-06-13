"""Common Session and its fields
"""

import typing
from ..auth import AuthSession, SupabaseAuthSession
from ..dal.base import DataAccessObjects
from ..data.settings.session import get_setting as get_session_setting
from . import Session, SessionField
from ..log.main import get_logger
logger = get_logger(__name__)


class CommonSession(Session):

    def __init__(self, _id, /,
        daos: SessionField[DataAccessObjects],
        auth_session: SessionField[AuthSession]
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

    @classmethod
    def from_task(cls, task) -> typing.Self:

        authroization = task.get_prebody_item("authorization")
        if authroization:
            jwt_str = authroization[7:]  # strip 'Bearer ' prefix
        else:
            jwt_str = task.get_state_item("authorization")

        if not jwt_str:
            logger.warning('Cannot find valid JWT in headers or cookies')
            raise ValueError('JWT not found')
        
        auth_session = SessionField(SupabaseAuthSession.from_token(jwt_str))
        daos = SessionField(DataAccessObjects(auth_session.value))

        return cls.get_session(
            auth_session.value.id, 
            daos=daos, auth_session=auth_session
        )
    
    
