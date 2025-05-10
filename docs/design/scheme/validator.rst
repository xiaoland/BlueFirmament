Scheme Validator Design
=======================

碧霄数据模型之校验器模块的设计文档。

校验器的职责是检查值是否合法，不合法则报错。

校验器被用于：

- 为数据模型字段添加 :doc:`./converter` 无法涵盖的校验逻辑


Features
--------

Add custom validator to field
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Use ``@field_validator`` to decorate a function to add
  custom validation logic to a field.
- The decorated function should accept a positional argument which is value.
  And raise an exception if the value is invalid and returns `None` when valid.
- The docorated function can be async.
- The decorated function can be instance method, class method or static method.
    - If instance method, must be method of
      :class:`blue_firmament.scheme.main.BaseScheme`.
- If field not exists, :py:exc:`ValueError` will be raised.
- Validator will be called before value set to scheme.
  So don't access other fields in the validator.
  If needed, checkout model validator.

See also:

- `#24 Allow (user-defined) field validator <https://github.com/xiaoland/BlueFirmament/issues/24>`_

API Reference
-------------
See :doc:`/api/scheme/validator`
