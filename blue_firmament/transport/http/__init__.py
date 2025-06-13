"""HTTP transport module, based on the ASGI specification.
"""

__all__ = [
    "HTTPTransporter"
]

import datetime
import typing
from typing import Optional as Opt
import urllib.parse
from dataclasses import dataclass
from .main import HTTPTransporter


@dataclass
class Cookie:
    name: str
    value: str
    path: Opt[str] = None
    domain: str = ''
    secure: bool = False
    '''如果为True，则只能在HTTPS协议下使用该Cookie'''
    httponly: bool = False
    '''JavaScript可否（False为可以）访问该Cookie'''
    expires: Opt[datetime.datetime] = None
    '''过期时间（datetime.datetime对象）'''
    max_age: int = 0
    '''最大存活时间（单位：秒）'''
    same_site: typing.Optional[typing.Union[typing.Literal['Lax'], typing.Literal['Strict']]] = None

    def dump_to_str(self) -> str:
        """Dump to string.
        
        Behaviours
        ----------
        - value will be url encoded
        """
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


