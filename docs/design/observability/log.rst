Log Design
==========

碧霄的日志系统的设计文档。

Purposes
--------

1. Trouble Shooting: locate problems efficiently

Structured and Centralized
--------------------------
Structured log is key for log tool to filter and search logs.
Therefore all logs are output in JSON format.

Write logs into file system, and use logrotate to manage log files.
(logrotate will be configured automatically from logger setting)

Carry Useful Information
------------------------
When user report a problem, an identifier is needed to filter related logs.
This identifier should carried in every log related to the request.

In a word, this identifier is an information on request scope (level).

And to find out which line of code logged the log,
the log should also contain the file path and line number.

All symbol name should use ``__qualname__`` instead of ``__name__``.

Scope
^^^^^

Request Scope
+++++++++++++
- Trace ID
- Session: log when request created

Handler Scope
+++++++++++++
- Handler name

Validator Scope
+++++++++++++++
- Validator name
- Value: only logged when entering validator

Easy to log
-----------

Bounded Logger
^^^^^^^^^^^^^^
These loggers are bound with corresponding context.

- Module level logger (not recommended)
- App level logger (not recommended)
- Request level logger
- Manager level logger
- Handler level logger
- Scheme level logger
- Validator level logger

Decorators
----------

Manager handler decorator
^^^^^^^^^^^^^^^^^^^^^^^^^
- Add entrance log before calling handler. (Logged parameters)
- Replace manager level logger with handler level logger.
- Add exit log after handler returned. (Logged result)

This decorator will be automatically added to all manager handlers
(see :ref:`log_enhancements`).

Add this decorator manually for non-manager handlers
(includes manager protected/private methods)
to gain above benefits.

Get logger
^^^^^^^^^^

.. code-block:: python

    # module level logger
    from blue_firmament.log import get_logger
    logger = get_logger(__name__)
    # alt: logger = get_logger('Manager.PartnerRequest')

.. code-block:: python

    # manager level logger
    from blue_firmament.manager import BaseManager
    class AccountManager(BaseManager):

        def signup(self, email: str, password: str):

            # ...
            self.logger.error('email already exist', email=email)
            # {..., 'event': 'email already exist', 'email': email}

.. code-block:: python

    # handler level logger
    from blue_firmament.manager import BaseManager
    from blue_firmament.log import LoggerT, log_handler
    class AccountManager(BaseManager):

        @log_handler(
            disabled_args=['password'],
        )
        def signup(self, email: str, password: str, logger: LoggerT):

            # ...
            logger.error('email already exist')
            # {..., 'event': 'email already exist', 'email': email}

Easy to read
------------


信息
--------

每个日志一定包含这些信息：

- `trace_id`: 追踪ID。这是跨服务跨应用的请求唯一标识
- `level`：日志级别
- `event`：日志描述信息
- `datetime`：日志发生时间，格式为 ISO 8601
- 在哪里发生
    - `pathname`：文件位置
    - `lineno`：行数
- 其它的关键上下文

ERROR 级别以上的日志一定有：

- `error_code`：错误码
    - 字符串
    - 使用 `_` 分级
    - 全大写

See Also
--------
- `#21 <https://github.com/xiaoland/BlueFirmament/issues/21>`_
