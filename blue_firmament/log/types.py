"""Type definitions for the log module."""

__all__ = [
    "LoggerT",
]

import structlog

LoggerT = structlog.stdlib.BoundLogger
