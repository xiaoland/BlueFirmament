Exception Design
================

碧霄异常系统的设计文档。

Purpose
-------

Built-in Exception
------------------

BlueFirmament built-in exception extends python built-in exception to provide
better error handling and reporting.

Raise
^^^^^
Raise exception should be easy.

Normally, exception instantiation accepts a message and keword arguments.
(Keyword arguments will be treated as context information)

Report to User
--------------

记录
------
异常被捕获后应当记录到日志系统中。

呈现给用户
----------
将异常信息呈现给用户，有助于用户排查问题、告知用户的用户产生问题的原因等等。

传输层会捕获请求处理器 / 连接处理器产生的异常，而后调用异常的序列化方法，将异常信息应用到响应中，而后返回响应给用户。
是“应用”而不是“序列化”，因为异常信息可能反映到响应的 header、body、status_code 中。

内置异常
--------
Python 提供的异常类型对于业务需求来说不够用，我们添加了这些异常类型，查阅 :doc:`../api/exception` 了解更多。

Features
--------

Reuse logger context
^^^^^^^^^^^^^^^^^^^^^
- Like logger, exception can hold a context.
  The context can be created (updated) from logger.
  (See :doc:`/design/observability/log` for more details)
- To apply logger context to exception,
  you can pass ``logger`` keyword argument to exception constructor,
  or create an exception from logger.

See Also
--------
- `#11 <https://github.com/xiaoland/BlueFirmament/issues/11>`_
