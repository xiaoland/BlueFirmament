"""BlueFirmament Transport Module

Include modules that listening to incoming requests, maintaining the connection, and sending responses after defined routing and handling.

"""


import enum


class ConnectionType(enum.Enum):
    
    TCP = 'tcp'
    UDP = 'udp'
    HTTP = 'http'
    HTTPS = 'https'
    WS = 'ws'
    WSS = 'wss'

    @classmethod
    def from_asgi_scheme(cls, scheme: str) -> 'ConnectionType':
        """从ASGI协议中获取连接类型"""
        if scheme == 'http':
            return cls.HTTP
        elif scheme == 'https':
            return cls.HTTPS
        elif scheme == 'ws':
            return cls.WS
        elif scheme == 'wss':
            return cls.WSS
        else:
            raise ValueError(f"Unsupported ASGI scheme: {scheme}")


class TransportOperationType(enum.Enum):
    """碧霄支持的操作类型"""

    GET = 'GET'
    POST = 'POST'
    PUT = 'PUT'
    PATCH = 'PATCH'
    DELETE = 'DELETE'
    OPTIONS = 'OPTIONS'


class TransportType(enum.Enum):
    """碧霄支持的传输层类型"""

    HTTP = 'http'


class HeaderName(enum.Enum):
    """碧霄支持的头名"""

    AUTHORIZATION = "authorization"
    CONTENT_TYPE = "content-type"
    CONTENT_ENCODING = "content-encoding"
    COOKIE = "cookie"


class ContentType(enum.Enum):
    """碧霄支持的内容类型"""

    JSON = 'application/json'
    XML = 'application/xml'
    FORM = 'application/x-www-form-urlencoded'
    TEXT = 'text/plain'
    BINARY = 'application/octet-stream'


class ResponseStatus(enum.Enum):
    """碧霄支持的响应状态"""

    OK = 200
    CREATED = 201
    NO_CONTENT = 204
    BAD_REQUEST = 400
    UNPROCESSABLE_ENTITY = 422
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    UNAVAILABLE_FOR_LEGAL_REASONS = 451
    INTERNAL_SERVER_ERROR = 500
