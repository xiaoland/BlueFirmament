import enum

from blue_firmament.event import EventStatus


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


TStatus2HCode: dict[EventStatus, int] = {
    EventStatus.OK: 200,
    EventStatus.DELETED: 204,
    EventStatus.CREATED: 201,
    EventStatus.BAD_REQUEST: 400,
    EventStatus.CONFLICT: 409,
    EventStatus.FORBIDDEN: 401,
    EventStatus.NOT_FOUND: 404,
    EventStatus.UNAUTHORIZED: 403,
    EventStatus.UNPROCESSABLE_ENTITY: 422,
    EventStatus.UNAVAILABLE_FOR_LEGAL_REASONS: 451,
    EventStatus.INTERNAL_SERVER_ERROR: 500,
}
"""Map Event status code to HTTP status code
"""
