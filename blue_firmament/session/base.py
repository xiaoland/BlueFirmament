

import abc
import datetime
import typing
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
    def updated_at(self):
        return self.__updated_at

    @property
    def value(self):
        return self.__value
    @value.setter
    def value(self, value: SFValueTV): 
        self.__value = value

    def destroy(self) -> None:
        pass

    def is_expired(self) -> bool:
        """Tell whether this field is expired.

        Always False by default, subclasses should override this method.
        """
        return False

    def refresh(self) -> None:
        pass

    @classmethod
    def from_task(cls, task: 'Task') -> typing.Self:
        raise NotImplementedError("this field not support from_task method")

    
class Session(abc.ABC):
    """BlueFirmament Session base class
    """

    INACTIVE_THRESHOLD = 300
    """unit: seconds"""
    REMOVE_BATCH_SIZE = 10
    """how many sessions to remove once session pool is full"""
    SESSION_POOL_MAX = 1000
    """max session cached in session pool"""

    __session_pool__: dict[str, typing.Self] = {}
    # TODO use remote storage to share session and save local memory (but performance cost?)
    """session cache pool"""
    __fields__: tuple[str, ...] = ()
    """all field's name"""

    def __init__(self, _id: str, /, **fields: SessionField) -> None:
        # metadata (not session fields, raw value)
        self.__id: str = _id
        self.__last_used_at: datetime.datetime = get_datetimez()

        self.__init_fields__(**fields)

    @abc.abstractmethod
    def __init_fields__(self, **fields: SessionField):
        ...

    @property
    def id(self):
        """Session ID"""
        return self.__id

    @property
    def last_used_at(self):
        return self.__last_used_at

    def update_last_used_at(self):
        self.__last_used_at = get_datetimez()

    def is_expired(self) -> bool:
        """Any field expired makes session expired.

        Will refresh expired fields first, if still expired, return True.
        """
        for field_name in self.__fields__:
            field = getattr(self, f"_{self.__class__.__name__}__{field_name}")
            if isinstance(field, SessionField):
                if field.is_expired():
                    field.refresh()
                    if field.is_expired():
                        return True
        return False

    def is_inactive(self) -> bool:
        """A span of time has passed since last use.
        """
        return get_datetimez() - self.__last_used_at > datetime.timedelta(seconds=self.INACTIVE_THRESHOLD)

    @classmethod
    def cleanup_sessions(cls) -> None:
        """Delete expired, inactive sessions from session pool.

        TODO run periodically.
        """
        to_delete = []

        for _id, session in cls.__session_pool__.items():
            if session.is_expired() or session.is_inactive():
                to_delete.append(_id)

        if (len(cls.__session_pool__) - len(to_delete)) >= cls.SESSION_POOL_MAX:
            # randomly remove a batch of sessions
            to_delete_len = len(to_delete)
            for key in cls.__session_pool__.keys():
                to_delete.append(key)
                if (len(to_delete) - to_delete_len) >= cls.REMOVE_BATCH_SIZE:
                    break

        for _id in to_delete:
            del cls.__session_pool__[_id]

    @classmethod
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
        session.update_last_used_at()
        return session
    
    @classmethod
    @abc.abstractmethod
    def from_task(cls, task: 'Task') -> typing.Self:
        """Create a session from a task
        """
        ...

