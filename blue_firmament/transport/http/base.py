import enum

from blue_firmament.task import TaskStatus


class MIMEType(enum.Enum):
    JSON = 'application/json'
    XML = 'application/xml'
    FORM = 'application/x-www-form-urlencoded'
    TEXT = 'text/plain'
    EVENT_STREAM = 'text/event-stream'
    BINARY = 'application/octet-stream'


class HTTPHeader(enum.Enum):
    AUTHORIZATION = "authorization"
    CONTENT_TYPE = "content-type"
    CONTENT_ENCODING = "content-encoding"
    ACCEPT = "accept"
    ACCEPT_CHARSET = "accept-charset"
    COOKIE = "cookie"
    SET_COOKIE = "set-cookie"
    CACHE_CONTROL = "cache-control"
    CONNECTION = "connection"
    TRACE_ID = "x-trace-id"
    CLIENT_ID = "x-client-id"


TStatus2HCode: dict[TaskStatus, int] = {
    TaskStatus.OK: 200,
    TaskStatus.NO_CONTENT: 204,
    TaskStatus.CREATED: 201,
    TaskStatus.BAD_REQUEST: 400,
    TaskStatus.CONFLICT: 409,
    TaskStatus.FORBIDDEN: 401,
    TaskStatus.NOT_FOUND: 404,
    TaskStatus.UNAUTHORIZED: 403,
    TaskStatus.UNPROCESSABLE_ENTITY: 422,
    TaskStatus.UNAVAILABLE_FOR_LEGAL_REASONS: 451,
    TaskStatus.INTERNAL_SERVER_ERROR: 500,
}
"""Map Task status code to HTTP status code
"""
