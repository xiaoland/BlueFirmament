"""请求上下文
"""

import typing
from typing import Optional as Opt, Annotated as Anno, Literal as Lit

import structlog

from ..session import SessionTV, CommonSession, Session
from ..dal.base import DataAccessObject
from .request import Request
from .response import Response
from ..scheme import BaseScheme, PrivateField, FieldT


class RequestContext(typing.Generic[SessionTV]):

    def __init__(self,
        request: Request[SessionTV],
        response: Response,
        app_logger: structlog.stdlib.BoundLogger,
        path_params: Opt[typing.Dict[str, typing.Any]] = None,  # TODO PathParamsT
    ):
        self._request = request
        """请求对象"""
        self._response = response
        """响应对象"""
        self._path_params = path_params or {}
        """路径参数"""
        self._query_params = request.query_params
        """查询参数"""
        self._logger = app_logger.bind(
            trace_id=request.trace_id,
        )
        """请求级别日志记录器"""
        self._session = request.session
        """会话对象"""
        if isinstance(request.session, CommonSession):
            self._dao = request.session.dao
            """数据访问对象"""
            self._operator = request.session.operator
            """请求者 / 操作员"""
        
        # TODO raise issue if not CommonSession ? or let it be None

    def init_from_rc(self, request_context: 'RequestContext'):

        """从另一个请求上下文初始化
        """
        self._request = request_context._request
        self._response = request_context._response
        self._path_params = request_context._path_params
        self._logger = request_context._logger
        self._session = request_context._session
        self._dao = request_context._dao
        self._operator = request_context._operator


class SchemeHasRequestContext(BaseScheme):

    _request_context: FieldT[RequestContext] = PrivateField()

    @property
    def _request(self):
        """请求对象"""
        return self._request_context._request
    @property
    def _response(self):
        """响应对象"""
        return self._request_context._response
    @property
    def _path_params(self):
        """路径参数"""
        return self._request_context._path_params
    @property
    def _query_params(self):
        """查询参数"""
        return self._request_context._query_params
    @property
    def _logger(self):
        """请求级别日志记录器"""
        return self._request_context._logger
    @property
    def _session(self):
        """会话对象"""
        return self._request_context._session
    @property
    def _dao(self):
        """数据访问对象"""
        return self._request_context._dao
    @property
    def _operator(self):
        """请求者 / 操作员"""
        return self._request_context._operator
