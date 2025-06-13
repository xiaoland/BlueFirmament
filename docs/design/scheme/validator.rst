Scheme Validator Design
=======================

BlueFirmament scheme validator's design doc.

Validator is resposible to ensure the value is legal,
if not, raise an excpetion.

Validator is used to add validation logic
that :doc:`./converter` cannnot covered.



Field Validator
---------------
A field validator will be ran on everytime the field set.
(Not including mutable field value changes.)

Registery
^^^^^^^^^
- Use ``@field_validator``

Mode
^^^^
You can set mode to ``before`` or ``after``

``before`` will run validator when field set in scheme instantiation process,
which means you shouldn't access other fields in the validator.

``after`` will run validator after scheme instantiated.
(immediately after scheme instantiated and when further field set)

Order
^^^^^
There's an implict order to run validators.
Should pay attention to this, especially for after mode validators.

Guideline
^^^^^^^^^
- The decorated function should accept a positional argument which is value.
  (The value hasn't set to scheme yet, but already converted)
- Raise :py:exc:`ValueError` if the value is invalid
  and returns ``None`` when valid.
- The docorated function can be async.
- The decorated function must be method of
  :class:`blue_firmament.scheme.main.BaseScheme`.
- Don't upate to DAL in validator.
  You can modify instance and left it to manager.
- Don't do any permission checking in validators,
  it's out of the boundary of scheme.

See also
^^^^^^^^

- `#24 Allow (user-defined) field validator <https://github.com/xiaoland/BlueFirmament/issues/24>`_
- `#36 Field validator can choose to run before or after instantiation <https://github.com/xiaoland/BlueFirmament/issues/36>`_
- `Infer function argument types from decorator #6905 <https://github.com/microsoft/pyright/issues/6905#issuecomment-1898152431>`_
    - for why field_decorator cannot enable decorated
      function paramter type to be inferred as field value type.


Model Validator
---------------
Or scheme validator.

Logging Enhancement
-------------------

- Validator level logger will replace scheme level logger.
- Validator level logger is inherited from scheme level logger.
- Validator level logger context includes:
    - Which validator (decorated function's name)
- Following info will be logged before entering the validator:
    - Which scheme and field
    - Cuurent scheme or field's value


Inheritance
-----------
Disable inheritance of validators by set
``__inherit_validators__ = False`` in scheme.


API Reference
-------------
See :doc:`/api/scheme/validator`
