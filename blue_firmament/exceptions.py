"""BlueFirmament TopLevel Exceptions

TODO exception factory to manage logger automatically
"""

__all__ = [
    'BlueFirmamentException',
    'BFExceptionTV',
    'InternalError',
    'ClientError',
    'RequestFailed',
    'ExternalError',
    'Retryable',
    'MaxRetriesExceeded',
    'ParamsInvalid',
    'AtLeastOne',
    'NotImplemented',
    'NotFound',
    'DuplicateOrConflict',
    'Duplicate',
    'Conflict',
    'InvalidStatusTransition', 
    'Unauthorized',
    'Forbidden'
]

import enum
import abc
import typing
from typing import Optional as Opt, Annotated as Anno, Literal as Lit
from .utils.typing_ import JsonDumpable
from .task import TaskStatus
from .log.main import get_logger
LOGGER = get_logger(__name__)
"""默认日志记录器
"""

if typing.TYPE_CHECKING:
    import requests
    from .scheme import BaseScheme  


BFExceptionTV = typing.TypeVar("BFExceptionTV", bound="BlueFirmamentException")
"""碧霄异常类型变量"""
class BlueFirmamentException(Exception, abc.ABC):

    """碧霄异常基类

    :ivar errmsg: 错误描述
    :ivar 

    """

    def __init__(self, 
        errmsg: str | dict = 'Exception occured', 
        *args, **kwargs
    ):
        if isinstance(errmsg, str):
            errmsg = {"errmsg": errmsg}
        
        self.errmsg: dict = errmsg

        super().__init__(errmsg, *args, **kwargs)

    def apply_to_task_result(self, response) -> None:
        """将异常序列化为响应体

        直接修改已有的响应对象的数据

        :param response: 响应对象
        """

    def dump_to_jsonable(self) -> JsonDumpable:
        """序列化为可JSON序列化的类型
        """
        return self.errmsg
    
    @property
    @abc.abstractmethod
    def task_status(self) -> TaskStatus:
        ...

    @classmethod
    def from_python_exception(cls, exception: Exception) -> "BlueFirmamentException":
        """从Python异常创建碧霄异常

        :param exception: Python异常
        """
        if isinstance(exception, ValueError):
            return ParamsInvalid()
        
        return InternalError()
    
    @property
    def name(self) -> str:
        """异常名称"""
        return self.__class__.__name__
    
    def dump_details_to_str(self) -> str:
        """将详细信息序列化为字符串
        """
        return '\n'.join([
            f"{k}: {v}"
            for k, v in self.errmsg.items()
        ])
    
    def dump_details_to_dict(self) -> dict:
        """将详细信息序列化为字典
        """
        return self.errmsg
    
    def __str__(self) -> str:
        return f"{self.name}: \n{self.dump_details_to_str()}"


class InternalError(BlueFirmamentException):
    """Exception raised cause of server's fault.
    """

    @property
    def task_status(self) -> TaskStatus:
        return TaskStatus.INTERNAL_SERVER_ERROR


class ClientError(BlueFirmamentException):
    """Exception raised cause of client's fault
    """

    @property
    def task_status(self) -> TaskStatus:
        return TaskStatus.BAD_REQUEST


class RequestFailed(InternalError):

    """请求失败

    请求没有到达目标服务
    """

    def __init__(self, 
        response: "requests.Response", 
        *args, **kwargs
    ):

        super().__init__(
            {
                "response": response
            }, 
            logger, *args, **kwargs
        )


class ExternalError(BlueFirmamentException):

    """外部错误

    任何外部应用程序与服务导致的异常都将转换为该异常
    """

    def __init__(self, 
        service_name: str, 
        logger=LOGGER,
        **errinfo: typing.Any,
    ):
        
        """
        :param service_name: 外部服务名称
        :param errcode: 错误码
            
            可以是错误码、错误信息等
        """

        super().__init__({
            "service_name": service_name,
            **errinfo
        }, logger)

    def __getitem__(self, key: str) -> typing.Any:
        """获取错误信息"""
        return self.errmsg[key]

    @property
    def task_status(self):
        return TaskStatus.SERVICE_UNAVAILABLE


class Retryable(BlueFirmamentException):
    """The exception can be eliminated by retrying the operation.
    """

    def __init__(
        self,
        delay: float = 0.2
    ):
        """
        :param delay: retry after this many seconds
        """
        super().__init__("please retry after %s seconds" % delay)
        self.__delay = delay

    @property
    def delay(self) -> float:
        return self.__delay

    @property
    def task_status(self):
        return TaskStatus.SERVICE_UNAVAILABLE


class MaxRetriesExceeded(BlueFirmamentException):

    def __init__(self):
        super().__init__("max retries exceeded")

    @property
    def task_status(self) -> TaskStatus:
        return TaskStatus.SERVICE_UNAVAILABLE


class ParamsInvalid(ClientError, ValueError):

    """参数无效

    场景
    ------
    - 类型不合法
    - 值不合法
    - 缺少参数
    - 通过参数获得（计算、数据库访问）的值不合法
    """

    def __init__(self,
        msg: str = '',
        **params
    ):

        """
        :param msg: 附加描述
        :param params: 参数名和参数值
        """
        super().__init__("invalid parameter(s), %s" % msg, params=params)


    @property
    def task_status(self):
        return TaskStatus.UNPROCESSABLE_ENTITY
    

class ParamRequired(ClientError, ValueError):
    """Exception for not giving required parameter.
    """

    def __init__(self, param_name: str, **kwargs):
        super().__init__("parameter required", param=param_name)


class AtLeastOne(ParamsInvalid):

    """至少需要一个参数

    在这些参数中，至少提供一个（有效）
    """

    def __init__(self, 
        *params: typing.Any,
        logger=LOGGER,
    ):
        
        """
        :param params: 参数名称
        """
        self.__params = params

    def __str__(self) -> str:
        
        return f"{self.name}: at least one of following parameters should be provided:\n" + \
            "\n    ".join(self.__params)
    

class NotImplemented(InternalError, NotImplementedError):

    def __init__(self, 
        service_name: str, 
        *args, **kwargs
    ):
        
        """
        :param service_name: 未实现的服务名
        """
        errmsg = "service %s is not implemented" % service_name
        super().__init__(errmsg, logger, *args, **kwargs)

    @property
    def task_status(self) -> TaskStatus:
        return TaskStatus.NOT_IMPLEMENTED

class NotFound(ClientError, KeyError):
    """未找到
    """

    @property
    def task_status(self) -> TaskStatus:
        return TaskStatus.NOT_FOUND

class DuplicateOrConflict(InternalError):

    """冲突或重复
    """

    def __init__(self, 
        *resource: tuple[typing.Any, typing.Any],
        operation: str,
        msg: str = '',
    ):
        
        """
        :param resource: 资源的的元组
            用（资源名，资源标识符）表示一个资源实例
        :param operation: 正在对资源进行的操作
        :param errmsg: 附加描述
        """

        super().__init__(
            f"Cannot perform {operation} on {resource[0]}: {resource[1]} cause: \n{msg}")

    @classmethod
    def from_scheme(cls, 
        scheme: "BaseScheme",
        operation: str,
        errmsg: str = '',
    ) -> 'DuplicateOrConflict':
        
        """从数据模型 实例创建冲突异常
        """
        return cls(
            (scheme.dal_path(), scheme[scheme.get_key_field()]),
            operation=operation, msg=errmsg,
        )

    @property
    def task_status(self) -> TaskStatus:
        return TaskStatus.CONFLICT


class Duplicate(DuplicateOrConflict):

    def __init__(self, msg: str):
        self.__msg = msg

    def dump_details_to_str(self) -> str:
        return self.__msg


class Conflict(DuplicateOrConflict):

    def __init__(self, msg: str, **kwargs):
        self.__msg = msg
        self.__context = kwargs

    def dump_details_to_str(self) -> str:
        return self.__msg


class InvalidStatusTransition(DuplicateOrConflict):

    """无效的状态转换

    不可以从当前状态切换到目标状态
    """
    def __init__(self,
        status_name: str,
        current_status, target_status
    ):
        
        self.__status_name = status_name
        self.__current_status = current_status
        self.__target_status = target_status

    @classmethod
    def from_enum_member(cls,
        current: enum.Enum, target: enum.Enum
    ) -> typing.Self:
        
        """从枚举成员创建
        """
        return cls(
            current.__class__.__name__,
            current.value, target.value
        )

    def dump_details_to_str(self) -> str:
        return f"cannot transist {self.__status_name} from {self.__current_status} to {self.__target_status}"


class Unauthorized(InternalError):
    """未认证
    """

    def __init__(self, 
        msg: Opt[str] = None,
        identity: Opt[str] = None,
        *args, **kwargs
    ):
        """
        :param identity: 导致未认证时使用的凭证（如果有）
        """
        super().__init__(
            'you are using identity (token): \n%s' % identity
        )

    @property
    def task_status(self) -> TaskStatus: 
        return TaskStatus.UNAUTHORIZED

        
class Forbidden(InternalError):

    """无权操作
    """

    def __init__(self, 
        msg: str,
    ):
        super().__init__(msg)

    @property
    def task_status(self): 
        return TaskStatus.FORBIDDEN


# class UnavailableForLegalReasons(BlueFirmamentException):

#     def __init__(self, errmsg, *args, **kwargs) -> None:

#         super().__init__(451, "Unavailable For Legal Reasons, %s" % errmsg, *args, **kwargs)


# class TooManyRequests(BlueFirmamentException):

#     def __init__(self, errmsg, *args, **kwargs) -> None:

#         super().__init__(429, "Too many request, limit reached. %s" % errmsg, *args, **kwargs)
