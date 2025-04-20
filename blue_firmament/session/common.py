"""
TODO
----
- 复用从 request 解析 JWT 的逻辑
- 复用同一 request 的 JWT 解析结果
"""


from ..dal.base import DataAccessObject
from ..dal.postgrest_dal import PostgrestDataAccessObject
from ..data.settings.session import get_setting as get_session_setting
from . import Session, SessionField
from ..transport import HeaderName
from ..log import get_logger

import typing
import jwt
import uuid


logger = get_logger(__name__)


class DAOSessionField(SessionField[DataAccessObject]):

    def __init__(self, value: DataAccessObject):
        super().__init__(value)

    @classmethod
    def from_request(cls, request):
        
        '''
        根据DAL配置选择合适的创建方式

        Behaviour
        ----------
        - 从请求头 `Authorization` 中创建与会话权限一致的PostgrestDAO
        - 如果没有请求头
        '''
        token = request.get_header(HeaderName.AUTHORIZATION)
        if token:
            token = token[7:]
            dao = PostgrestDataAccessObject(token=token)
        else:
            dao = PostgrestDataAccessObject.ANON_DAO

        return cls(dao)


class JWTSubSessionField(SessionField[str | None]):

    def __init__(self, value: str | None):
        super().__init__(value)

    @classmethod
    def from_request(cls, request):

        jwt_str = request.get_header(HeaderName.AUTHORIZATION)
        if jwt_str:
            jwt_str = jwt_str[7:]  # strip 'Bearer ' prefix
            try:
                payload = jwt.decode(
                    jwt_str,
                    get_session_setting().jwt_secret_key,
                    algorithms=(get_session_setting().jwt_algorithm,),
                    options={
                        'verify_signature': False
                    },
                )
                sub = payload.get('sub')
                if not isinstance(sub, str):
                    raise ValueError('sub not found or invalid')
            except jwt.exceptions.PyJWTError as e:
                logger.warning('JWT decode failed', e)
                raise ValueError('JWT decode failed')
        else:
            sub = None

        return cls(sub)


class CommonSession(Session):

    '''通用会话类

    包含下列字段：
    - dao：数据访问对象（DAO）
    - account_id: 当前会话使用的凭证（JWT）是哪个用户的
    '''

    def __init__(self, _id, /,
        dao: SessionField[DataAccessObject],
        account_id: SessionField[str] = SessionField(''),
    ) -> None:

        super().__init__(_id)

        self.__dao: SessionField[DataAccessObject] = dao
        self.__account_id: SessionField[str] = account_id

    @property
    def dao(self):
        return self.__dao.value
    
    @property
    def account_id(self):
        return self.__account_id.value
    
    def is_me(self, other_account_id: str) -> bool:
        return self.account_id == other_account_id

    @classmethod
    def from_request(cls, request) -> typing.Self:

        '''
        '''
        # get _id from JWT or uuid
        try:
            # try headers first
            jwt_str = request.get_header(HeaderName.AUTHORIZATION)
            if jwt_str:
                jwt_str = jwt_str[7:]  # strip 'Bearer ' prefix
            else:
                # try cookies
                jwt_str = request.get_cookie(HeaderName.AUTHORIZATION.value)

                if not jwt_str:
                    logger.warning('Cannot find valid JWT in headers or cookies')
                    raise ValueError('JWT not found')
                else:
                    jwt_str = jwt_str.value

            try:
                jwt_payload: dict = jwt.decode(
                    jwt_str,
                    get_session_setting().jwt_secret_key,
                    options={
                        'verify_signature': False
                    },
                    algorithms=(get_session_setting().jwt_algorithm,)
                )
            except jwt.exceptions.PyJWTError as e:
                logger.warning('JWT decode failed', e)
                raise ValueError('JWT decode failed')
            else:
                session_id = jwt_payload.get('session_id')

                if not isinstance(session_id, str):
                    raise ValueError('_JWT_PAYLOAD_FIELD_NAME not found or invalid')
        except ValueError:
            session_id = uuid.uuid4().hex

        # get dao
        dao = DAOSessionField.from_request(request)

        # get account_id
        account_id = JWTSubSessionField.from_request(request)

        return cls.get(session_id, True, dao=dao, account_id=account_id)
    
    
