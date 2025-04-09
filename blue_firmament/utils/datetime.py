"""
author: Lan_zhijiang
date: 2024-11-10
desc: 时间日期工具函数
issues: 

references: 
    https://git.hadream.ltd/anana/backend/common/-/wikis/Util/Datetime
"""

import datetime
import time

# settings
from ..data.settings.base import get_setting as get_base_setting


def get_timezone(timezone_delta: int = get_base_setting().timezone_delta) -> datetime.timezone:

    """
    获取时区对象
    """
    return datetime.timezone(datetime.timedelta(hours=timezone_delta))

def get_datetimez(
    rfc3339: str | None = None,
    timestamp: float | None = None,
    iso8601: str | None = None,
    timezone: datetime.timezone = get_timezone(),
) -> datetime.datetime:

    """
    获取当前时间对象（带时区）

    :param rfc3339: RFC3339格式时间字符串，如"2024-11-10T12:00:00+08:00"
    :param timestamp: 时间戳（秒级浮点）
    :param iso8601: ISO8601格式时间字符串，如"2024-11-10 12:00:00"
    :param timezone: 时区对象，如get_timezone(8)

    Exceptions
    ^^^^^^^^^^
    - ValueError: 如果rfc3339或iso8601都未提供，则抛出异常
    """
    if timestamp:
        return datetime.datetime.fromtimestamp(timestamp, tz=timezone)
    if rfc3339 or iso8601:
        val = rfc3339 or iso8601
        if val is None:
            raise ValueError("rfc3339 or iso8601 must be provided")
        return datetime.datetime.fromisoformat(val)
    return datetime.datetime.now(tz=timezone)

def get_datetime(timestamp: float | None = None) -> datetime.datetime:

    """
    获取当前时间对象（不带时区）
    """
    if timestamp:
        return datetime.datetime.fromtimestamp(timestamp)
    return datetime.datetime.now()

def get_timestamp(datetime_obj: datetime.datetime | None = None, rfc3339: str | None = None) -> float:

    """
    获取时间戳（秒级浮点）
    """
    if datetime_obj:
        return datetime_obj.timestamp()
    if rfc3339:
        return datetime.datetime.fromisoformat(rfc3339).timestamp()
    return time.time()

def get_rfc3339(timestamp: float | None = None, datetime_obj: datetime.datetime | None = None) -> str:

    """
    获取RFC3339格式时间
    """
    if timestamp:
        return datetime.datetime.fromtimestamp(timestamp).isoformat()
    elif datetime_obj:
        return datetime_obj.isoformat()
    
    raise ValueError("timestamp or datetime_obj must be provided")

def format_datetime(datetime: datetime.datetime, format: str = "%Y-%m-%d %H:%M:%S") -> str:

    """
    格式化时间对象
    """
    return datetime.strftime(format)

def format_timestamp(timestamp: float, format: str = "%Y-%m-%d %H:%M:%S") -> str:

    """
    格式化时间戳
    """
    return datetime.datetime.fromtimestamp(timestamp).strftime(format)