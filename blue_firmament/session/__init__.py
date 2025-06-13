"""会话模块
"""

import typing
from .base import Session, SessionField
from .common import CommonSession


SessionTV = typing.TypeVar('SessionTV', bound=Session)
