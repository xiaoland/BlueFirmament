Manager Design
==============

Purposes
--------
- 避免在处理器中通过参数传递请求上下文，将请求上下文藏入 ``self`` 中

BaseManager
-----------
.. _log_enhancements:

Log Enhancements
^^^^^^^^^^^^^^^^
- All handlers can get handler level logger from ``self``.
- Alhandlers extrance and exitrance will be logged automatically.

Handlers collaboration
^^^^^^^^^^^^^^^^^^^^^^
Call a handler or methods from another handler / methods of the same instance.

- ``self.get_scheme``: get the managing scheme ... is this a good design?
- Keep scheme consistent across handlers

CommonManager
-------------
封装常用的处理器，并可以动态生成处理器并注册到应用路由中

- 获取：``GET <manager_name>/<primary_key>``
- 获取字段：``GET <manager_name>/<primary_key>/<field_name>``
- 创建：``POST <manager_name>``
- 插入条目进字段：``PUT <manager_name>/<primary_key>/<field_name>``
- 修改：``PATCH <manager_name>/<primary_key>``
- 覆盖：``PUT <manager_name>/<primary_key>``
- 设置字段：``PUT <manager_name>/<primary_key>/<field_name>``
- 删除：``DELETE <manager_name>/<primary_key>``
- 从字段删除条目：``DELETE <manager_name>/<primary_key>/<field_name>``

与 :class:`blue_firmament.session.common.CommonSession` 结合使用

简化 :class:`blue_firmament.manager.BaseManager` 的使用

Use `get`, `update`, `put`, don't direcly use dao, or inner scheme's
consistency will be damadged.

Typed Manager
-------------
Typed manager manage part of the base scheme.

- Typed scheme
    - Same field as the base scheme, but some fields type are more specific
    - Few fields of the base scheme (includes primary key field)
- Get typed scheme instance
- Update typed scheme instance

Field Manager
-------------
A manager to manage a field of the base scheme.

依赖注入
^^^^^^^^^^^^^^^
- 自动注入请求上下文
    - `request`
    - `session`
    - `response`
    - `logger`
- 处理器可以直接使用 ``self.get_scheme`` 获取本次请求中所处理数据模型实例
- 处理器可以通过 ``self.get_scheme`` 以及主键，使用当前请求上下文的 DAO 获取数据模型实例
- 处理器可以通过 ``self.set_scheme`` 设置本次请求处理的数据模型实例，从而衔接本管理器中其它的处理器
- 使用 `self.derive_manager` 派生

.. code-block:: python

    class AccountManager(BaseManager[Account, CommonSession]):

        __path_prefix__: str = '/account'
        
        def sign_up(self, **data) -> Account:

            # build up scheme
            account = Account.from_no_primary_key(**data)

            # insert to db
            account = self.session.dao.insert(account)

            # for other methods to continue operations on current scheme
            self.set_scheme(account)

            self.verify_email()

            return self.scheme

        async def get(self, account_id: str) -> Account:

            account = await self.get_scheme(from_primary_key=account_id)

            if account_id != self.session.account_id:
                # return public version
                return account.public()
            else:
                return account


    # register router for manager handlers
    reg = app.get_manager_handler_route_record_register(
        manager=AccountManager,
    )
    # or AccountManager.get_route_record_register(app)
    reg(OpertationType.GET, "/{id}", AccountManager.get)
    reg(OpertationType.POST, "", AccountManager.sign_up)


Life Cycle
----------
- 在调用处理器时实例化
- 在响应结束后销毁

See Also
--------
- `#5 <https://github.com/xiaoland/BlueFirmament/issues/5>`_
- :doc:`../api/manager`
