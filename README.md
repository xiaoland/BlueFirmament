# Blue Firmament

> 中文名：碧霄
> 日语名：青空 (AoSora)

A backend framework for Python applications that covers all you need, and aims at building east-to-read, maintainable application.

## Installation

```bash
pip install blue-firmament
```

## Usage

```python
import blue_firmament

# 获取日志器
import blue_firmament.log
logger = blue_firmament.log.get_logger(__name__)

# 覆盖设置
from app.data.settings.base import get_setting as get_base_setting
from app.data.settings.dal import get_setting as get_dal_setting

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

