

import abc
import typing
from ..utils.datetime import get_datetimez
from ..utils.datetime_ import get_datetimez
from ..data.settings.base import get_setting as get_base_setting

if typing.TYPE_CHECKING:
    from blue_firmament.task import Task


SFValueTV = typing.TypeVar("SFValueTV")
class SessionField(typing.Generic[SFValueTV], abc.ABC):

    '''会话字段类（抽象类）

    是状态的基本存储单位

    声明周期
    ^^^^^^^
    - 创建：在连接的第一个请求到达时初始化
    - 销毁
    - 重新创建
    - 刷新

    Example
    ^^^^^^^
    ```python
    class MySessionField(SessionField):
    
        def __init__(self):
            ...    
            super().__init__(value)
    ```
    '''

    def __init__(self, value: SFValueTV):
        self.__updated_at = get_datetimez()
        self.__value: SFValueTV = value
    
    @property
    def updated_at(self): return self.__updated_at

    @property
    def value(self): return self.__value

    @value.setter
    def value(self, value: SFValueTV): 
        self.__value = value

    def destory(self) -> None:
        raise NotImplementedError('destory() must be implemented in subclass')
    
    def refresh(self) -> None:
        pass

    @classmethod    
    def from_task(cls, task: 'Task') -> typing.Self:
        '''从请求中创建会话字段实例'''
        raise NotImplementedError()

    
class Session(abc.ABC):

    '''BlueFirmament Session baseclass
    
    用于存储与用户代理的会话信息，与传输层无关，是应用层的一部分

    Examples
    ^^^^^^^^
    ```python
    class MySession(Session):
    
        def __init__(self, _id: str, custom_field: SessionField[type]) -> None:
            
            super().__init__(_id)

            # other custom fields
            self.__custom_field = custom_field
    '''

    __sessions__: typing.Dict[str, typing.Self] = {} 
    '''全局会话实例池'''
    __fields__: typing.Tuple[str, ...] = ()
    '''会话字段列表（子类覆盖，补课修改）'''

    def __init__(self, _id: str, /, **fields: SessionField) -> None:

        '''实例化会话

        :param _id: 该会话的ID
        '''
        # metadata (not session fields, raw value)
        self.__id: str = _id
        self.__last_used_at: datetime.datetime = get_datetimez()

        self.__save_to_sessions()
        self.__init_fields__(**fields)

    def __save_to_sessions(self):
    @abc.abstractmethod
    def __init_fields__(self, **fields: SessionField):
        ...

        '''保存当前会话实例到会话池

        会运行一个后台任务（线程）检查整个会话池中是否有过期会话并清理
        '''
        self.__sessions__[self.__id] = self

        # TODO 需要考虑线程安全问题（多请求处理）

    @classmethod
    def check_sessions(cls) -> None:

        '''检查会话池

        - 如果会话实例过期，则删除该实例
        '''
        marked_for_deletion = []
        for _id, session in cls.__sessions__.items():
            if session.is_expired:
                marked_for_deletion.append(_id)

        for _id in marked_for_deletion:
            del cls.__sessions__[_id]

    @property
    def is_expired(self) -> bool:
        '''会话是否过期
        
        所有会话字段中最新的更新时间已经早于现在X秒以上
        '''
        # get newest updated_at
        newest_updated_at = max([getattr(self, field).updated_at for field in self.__fields__])
        # check if expired
        return (get_datetimez() - newest_updated_at).total_seconds() > get_base_setting().session_expire_time

    @classmethod
    def get_session(cls, _id: str, upsert: bool = True, /, **kwargs: SessionField) -> typing.Self:

        '''获取会话实例

        :param upsert: 不存在则创建新的会话实例（否则抛出KeyError）
        :param **kwargs: 其他字段（用于upsert）
        '''
        try:
            res = cls.__sessions__[_id]
        except KeyError:
            if upsert:
                res = cls(_id, **kwargs)
                cls.__sessions__[_id] = res
            else:
                raise KeyError(f'Session with id {_id} not found')
            
        return res
    def upsert(
        cls,
        _id: str,
        fields_getter: typing.Callable[[], dict[str, SessionField]],
    ) -> typing.Self:
        """

        :param _id: Session ID
        :param fields_getter: function returns fields for creating a new session.

        If session expire, recreate.
        """
        session = cls.__session_pool__.setdefault(_id, cls(_id, **fields_getter()))
        if session.is_expired():
            del cls.__session_pool__[_id]
            session = cls(_id, **fields_getter())
        return session
    
    @classmethod
    @abc.abstractmethod
    def from_task(cls, task: 'Task') -> typing.Self:
        """Create a session from a task
        """
        ...

