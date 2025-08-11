# Blue Firmament

> 中文名：碧霄
> 日语名：青空 (AoSora)

A backend framework for Python applications that covers all you need, and aims at building east-to-read, maintainable application.

## Features

- 任务处理器
    - 可以像普通函数一样调用，无需将业务逻辑和处理器拆成两个函数
- 数据模型
  - 数据模型方法中可以调用管理器的方法： `Manager(self._task_context)`（得继承同一个TaskContext）
  - 通过 dump_flag，不必为了 create, edit 去维护变体
  在创建只需 `**data.dump_to_dict()` ，编辑只需 `merge_scheme`即可将用户提交的新值保存
- DAL
  - 支持TableLike, KVLike, PubSubLike数据源
  - 支持鉴权（与会话同步）
  - 具体支持 PostgREST, Redis 数据源
  - 自动处理引用表查询 （A表引用B表，查询A表时直接使用 B.column.<filter>(...) 创建相应过滤器，过滤器会自动处理外键依赖）

## Installation

```bash
pip install blue-firmament
```

## Example

```python
# main.py
import blue_firmament

# 获取日志器
import blue_firmament.log
logger = blue_firmament.log.get_logger(__name__)

# 覆盖设置
from data.settings.base import get_setting as get_base_setting
from data.settings.dal import get_setting as get_dal_setting

import blue_firmament.main
from blue_firmament.transport.http import HTTPTransporter
from blue_firmament.session.common import CommonSession
app = blue_firmament.main.BlueFirmamentApp()

# 添加一个传输层
app.add_transporter(HTTPTransporter(
    app.handle_request, CommonSession, 
    host=get_base_setting().http_host, port=get_base_setting().http_port,
))

logger.info("Initializing BlueFirmament's Routers and Middlewares...")

# 配置数据访问层
from blue_firmament.dal import set_anon_dao
from blue_firmament.dal.postgrest_dal import PostgrestDataAccessObject
# 配置一个全局的ANON角色的PostgrestDAO实例，会话在无法获取到权限的时候会fallback到此
set_anon_dao(PostgrestDataAccessObject(
    token=get_dal_setting().postgrest_anonymous_token,
), PostgrestDataAccessObject)

# 声明数据模型
from blue_firmament.transport import TransportOperationType
from app.schemas.main import AccountProfile
# 基于数据模型添加CRUD服务
app.provide_crud_over_scheme('account', disabled_operations=(TransportOperationType.DELETE,))(AccountProfile)

# 启动服务
app.run()
```

### Manager

```python
# manager.py

import typing
from blue_firmament import listen_to, Method
from blue_firmament.manager import CommonManager
from blue_firmament.scheme import BusinessScheme
from blue_firmament.scheme.enum import Status
from blue_firmament.exceptions import Forbidden


class PRStatus(Status):
    DRAFT = "draft"
    EXECUTING = "executing"
    CANCELLED = "cancelled"
    
    def to_cancelled(self) -> typing.Self:
        return self._to_target_status(self.CANCELLED, self.DRAFT)

class PartnerRequest(BusinessScheme[int]):
    status: PRStatus
    created_by: str
    
    def is_admin(self, account_id: str) -> bool:
        return self.created_by == account_id

class PartnerRequestManager(CommonManager[PartnerRequest, int]):
  
    async def _must_be_admin(
        self,
        pr_id: None | int = None,
    ) -> None:
        self._scheme = await self._get_scheme(_id=pr_id)
        if not self._scheme.is_admin(self._operator.id):
            raise Forbidden("must be admin")
  
    @listen_to(Method.PUT, '/{pr_id}/cancel')
    async def cancel(
        self,
        pr_id: int
    ):
        self._scheme = self._get_scheme(pr_id)
        await self._must_be_admin()
        self._scheme.status.to_cancelled()
        await self._update_scheme()
        self._emit(".cancelled", pr_id=self._scheme._id)
        return self._scheme

```

## Documentation

To build the documentation:

```bash
# Install documentation dependencies
pip install -e ".[docs]"

# Build the documentation
cd docs
make html
```

After building, the documentation will be available in `docs/_build/html`.

