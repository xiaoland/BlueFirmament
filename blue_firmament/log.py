'''碧霄日志模块


'''

import structlog
import sys
import logging
from .data.settings.log import get_setting as get_log_setting

logging.basicConfig(
    format="[%(name)s][%(asctime)s] %(levelname)s: %(message)s", 
    level=get_log_setting().log_level,
)

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

def get_logger(name) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
