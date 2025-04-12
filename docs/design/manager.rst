Design of Manager
=================

设计理念
--------
- 避免在处理器中传递请求上下文数据，改用依赖注入的方式
- 

目标效果总结
------------

.. code-block:: python

    class AccountManager(BaseManager[Account, CommonSession]):

        __name__: str = 'account'
        
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


- 处理器无需从参数中获取请求上下文，可以从 ``self.session`` 中获取，省去了额外的参数
- 处理器可以直接使用 ``self.get_scheme`` 获取本次请求中所处理数据模型实例
- 处理器可以通过 ``self.get_scheme`` 以及主键，使用当前请求上下文的 DAO 获取数据模型实例
- 处理器可以通过 ``self.set_scheme`` 设置本次请求处理的数据模型实例，从而衔接本管理器中其它的处理器

API
---
跳转到 `Manager API Reference </api/manager>`_ 了解 API 细节
