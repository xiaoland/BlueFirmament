'''碧霄日志模块

See :doc:`docs/log`
'''

import logging
import typing
import structlog
from typing import Optional as Opt, Annotated as Anno
from ..data.settings.log import get_setting as get_log_setting

if typing.TYPE_CHECKING:
    from . import LoggerT


logging.basicConfig(level=get_log_setting().log_level)

logger_factory = None
log_file = get_log_setting().log_file
if log_file is not None:
    logger_factory = structlog.WriteLoggerFactory(
        file=open(log_file, mode="wt"),
    )
else:
    logger_factory = structlog.stdlib.LoggerFactory()

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.processors.TimeStamper(fmt="iso", key="datetime"),
        structlog.processors.dict_tracebacks,
        structlog.processors.CallsiteParameterAdder(
            parameters=[
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.LINENO,
            ]
        ),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=logger_factory,
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=get_log_setting().cache_logger_on_first_use,
)



def get_logger(name) -> "LoggerT":
    return structlog.get_logger(name)

def bind_logger_contextvars(**contextvars) -> None:
    structlog.contextvars.bind_contextvars(**contextvars)

def clear_logger_contextvars() -> None:
    structlog.contextvars.clear_contextvars()

