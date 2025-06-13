"""Auth module
"""

import abc
import jwt
import supabase_auth
import typing
from .exceptions import ParamsInvalid
from .data.settings.auth import get_setting as get_auth_setting
from .data.settings.session import get_setting as get_session_setting
from .log import get_logger
logger = get_logger(__name__)

if typing.TYPE_CHECKING:
    from blue_firmament.task import Task


UIDTV = typing.TypeVar("UIDTV")
class User(
    typing.Generic[UIDTV],
    abc.ABC
):
    
    SERV_ROLES: tuple[str] = ('service_role',)

    @classmethod
    @abc.abstractmethod
    def from_task(cls, task: 'Task') -> typing.Self:
        pass

    @classmethod
    @abc.abstractmethod
    def from_id(cls, uid: UIDTV) -> typing.Self:
        pass

    @classmethod
    @abc.abstractmethod
    def from_anon(cls) -> typing.Self:
        """Create an anonymous user"""

    @property
    @abc.abstractmethod
    def id(self) -> UIDTV:
        pass

    @property
    @abc.abstractmethod
    def roles(self) -> typing.Set[str]:
        pass

    def is_serv(self) -> bool:
        """Is user a serv role"""
        return any(
            role in self.SERV_ROLES
            for role in self.roles
        )


class SupabaseUser(User[str]):

    GOTRUE_CLIENT = supabase_auth.SyncGoTrueClient(
        url=get_auth_setting().supabase_auth_url,
        headers={
            'apiKey': get_auth_setting().supabase_serv_key,
            'authorization': f"Bearer {get_auth_setting().supabase_serv_key}"
        },
        auto_refresh_token=False,
        persist_session=False
    )

    def __init__(self,
        uid: str,
        roles: typing.Set[str]
    ) -> None:
        self.__uid = uid
        self.__roles = roles

    @classmethod
    def from_task(cls, task: 'Task') -> typing.Self:
        authorization = task.get_prebody_item("authorization")
        if authorization:
            jwt_str = authorization[7:]  # strip 'Bearer ' prefix
            try:
                jwt_payload: dict = jwt.decode(
                    jwt_str,
                    key=get_auth_setting().jwt_secret_key,
                    algorithms=(get_auth_setting().jwt_algorithm,)
                )
            except jwt.exceptions.PyJWTError as e:
                logger.warning('JWT decode failed', e)
                raise ValueError('JWT decode failed')
            else:
                roles = set()
                if jwt_payload.get('role'):
                    roles.add(jwt_payload.get('role'))
                return cls(
                    uid=jwt_payload.get('sub', ''),
                    roles=roles
                )
        else:
            logger.warning('Cannot find valid JWT in headers')
            return cls.from_anon()
    
    @classmethod
    def from_id(cls, uid: str) -> typing.Self:
        res = cls.GOTRUE_CLIENT.admin.get_user_by_id(uid)
        roles = set(res.user.role) if res.user.role else set()
        return cls(
            uid=uid, roles=roles
        )
    
    @classmethod
    def from_anon(cls) -> typing.Self:
        anon_user = cls.GOTRUE_CLIENT.sign_in_anonymously()
        if anon_user.user:
            roles = set(anon_user.user.role) if anon_user.user.role else set()
            return cls(
                uid=anon_user.user.id, roles=roles
            )
        else:
            raise ParamsInvalid("failed to create anon user")

    @property
    def id(self): return self.__uid

    @property
    def roles(self): return self.__roles


UserTV = typing.TypeVar("UserTV", bound=User)
class AuthSession(
    abc.ABC,
    typing.Generic[UserTV]
):

    def __init__(self,
        session_id: str,
        token: str,
        user: UserTV,
    ) -> None:
        self.__id = session_id
        self.__token = token
        self.__user = user

    @property
    def id(self): return self.__id
    @property
    def user(self): return self.__user
    @property
    def uid(self): return self.__user.id
    @property
    def token(self): return self.__token
    
    @classmethod
    @abc.abstractmethod
    def from_token(cls, token) -> typing.Self:
        ...

class SupabaseAuthSession(AuthSession[SupabaseUser]):

    @classmethod
    def from_token(cls, token: str) -> typing.Self:
        try:
            jwt_payload: dict = jwt.decode(
                jwt=token,
                key=get_session_setting().jwt_secret_key,
                algorithms=(get_session_setting().jwt_algorithm,)
            )
        except jwt.exceptions.InvalidSignatureError:
            logger.exception("JWT signature invalid")
            raise ParamsInvalid('JWT signature invalid')
        except jwt.exceptions.DecodeError as e:
            logger.exception('JWT decode failed')
            raise ParamsInvalid('JWT decode failed')
        else:
            return cls(
                session_id=jwt_payload['session_id'],
                token=token,
                user=SupabaseUser(
                    uid=jwt_payload['sub'],
                    roles=set(jwt_payload['role'])
                )
            )