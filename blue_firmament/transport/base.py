import typing
import datetime
import urllib.parse
import abc
from dataclasses import dataclass, InitVar

from ..scheme import BaseScheme
from . import ConnectionType

if typing.TYPE_CHECKING:
    from ..session import Session
    from .request import Request
    from .response import Response


RequestHandlerType = typing.Callable[
    ['Request', 'Response'], typing.Union[
        None, typing.Coroutine[None, None, None]
    ]
]
'''相对于传输层的请求处理器的类型'''
PeerInfo = typing.NewType('PeerInfo', typing.Tuple[str, int | None])
'''连接的对端信息'''


@dataclass
class Connection:

    '''碧霄连接类

    维持有关于该连接的信息
    '''

    type: InitVar[ConnectionType]
    transporter: InitVar['BlueFirmamentTransport']
    source: InitVar[typing.Optional[PeerInfo]] = None
    target: InitVar[typing.Optional[PeerInfo]] = None


class Cookie(BaseScheme):
    '''碧霄Cookie类'''
    
    name: str
    value: str
    path: typing.Optional[str] = None
    domain: str = ''
    secure: bool = False
    '''如果为True，则只能在HTTPS协议下使用该Cookie'''
    httponly: bool = False
    '''JavaScript可否（False为可以）访问该Cookie'''
    expires: typing.Optional[datetime.datetime] = None
    '''过期时间（datetime.datetime对象）'''
    max_age: int = 0
    '''最大存活时间（单位：秒）'''
    same_site: typing.Optional[typing.Union[typing.Literal['Lax'], typing.Literal['Strict']]] = None

    def dump(self) -> str:
        '''序列化为字符串
        
        传输Cookie时使用

        Behavior
        -----------
        value需要进行URL编码
        '''
        value: str = urllib.parse.quote(self.value, safe='')
        result = f'{self.name}={value};'
        if self.path:
            result += f' Path={self.path};'
        if self.domain:
            result += f' Domain={self.domain};'
        if self.secure:
            result += ' Secure;'
        if self.httponly:
            result += ' HttpOnly;'
        if self.expires:
            result += f' Expires={self.expires.strftime("%a, %d %b %Y %H:%M:%S GMT")};'
        if self.max_age:
            result += f' Max-Age={self.max_age};'
        if self.same_site:
            result += f' SameSite={self.same_site};'
        return result.strip()


ConnectionHandlerType = typing.Callable[['Connection'], None]
class BlueFirmamentTransport(abc.ABC):
    """The base class of the transport module."""

    def __init__(self, 
        req_handler: 'RequestHandlerType',
        session_cls: typing.Type['Session']
    ) -> None:

        self.__request_handler: 'RequestHandlerType' = req_handler
        self.__session_cls: typing.Type['Session'] = session_cls

    @abc.abstractmethod
    async def start(self):

        '''开始监听'''
        pass
