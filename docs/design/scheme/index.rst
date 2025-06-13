Scheme Design
=============

BlueFirmament scheme module's design.

Create scheme class
-------------------


Instantiation
-------------
1. Initialize instance variables.
2. Set field values (see more details at :ref:`field_set` ).
3. Run scheme level validators.
4. Run post init method.
5. Log instantiation if enabled.

Serialization
-------------
We use word ``dump`` to replace ``serialize``
and ``load`` to replace ``deserialize``.

Field
-----

.. _field_set:

Set
^^^
1. Is undefined,
   If yes and allow partial, value will be ``_undefinded``;
   If yes but not partial,
   use default value (raise ``ValueError`` if not configured).
2. Convert
3. Run field validators (see more details at :doc:`/design/scheme/validator`)
4. Proxy value if enabled
5. Save to scheme instance
6. Mark as dirty if this is not the init set

Partial
^^^^^^^
Partial fields' value remain ``_undefinded`` if not provided
when instantiation. (Default value will not be applied)

And ``exclude_unset=True`` will exclude these fields when
dumping. ()

How to make field partial?

- Make all fields in the scheme partial by set ``__partial__ = True``
- Or only this field is partial by ``field(is_partial=True)``

Others:

- Now work for private fields
- Partial will not works on composite field's sub fields
- Field level setting is prior to scheme level
- ``unset`` is the same as ``partial``

Boundary
--------
- Should not involve anything about field itself,
  scheme should pay attention to how fields work together.
- Scheme knows where itself stores or cached (in DAL).
- Value set should be idempotent.
- Methods should be idempotent.
- No interaction with Task, TaskResult or Session.

Best Practice
-------------
- Don't write DAL.
  Instead, change field value then leaves to manager.
- Use a sub scheme of base scheme, which enables ``__partial__``,
  as the type of edit, create request body. (And you can add
  extra fields on the sub scheme)
  In this case, handler needs to map allowed fields manually to
  the scheme going to be inseted  updated.

Access Control
--------------
- By Row
- By column
- By Behaviour
- By Role

Log Enhancement
---------------
Scheme level logger can be obtained from ``self._logger``.

Business Scheme
---------------
- ``inserted`` is a property indicates whether
  this instance is inserted to DAL.
  This is done by check ``_id`` field's value,
  if it's int, must greater than ``0``.


Sub Moudles
-----------
.. toctree::
    :maxdepth: 1

    ./validator
    ./converter
