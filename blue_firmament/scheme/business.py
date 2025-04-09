
from ..dal import DataAccessObject
from ..dal.filters import EqFilter
from .field import Field
from .main import BaseScheme
import typing


BusinessSchemeIDType = typing.TypeVar('BusinessSchemeIDType')
class BusinessScheme(BaseScheme, typing.Generic[BusinessSchemeIDType]):

    """碧霄标准业务数据模型类

    标准业务数据模型是其所在业务模块的核心数据模型，一定对应一张表。

    你仍然可以基于基本数据模型类定义自己的业务数据模型类

    特性
    ------

    主键
    ^^^^^
    主键为 ``_id`` （预定义）

    与数据访问层交互
    ^^^^^^^^^^^^^^^^

    自动业务接口
    ^^^^^^^^^^^^
    - 自动在路由器注册Restful风格的CURD接口
    """

    _id: BusinessSchemeIDType = Field(is_primary_key=True)

    @classmethod
    async def simple_fetch(cls, /, _id: BusinessSchemeIDType, _dao = None, **kwargs) -> typing.Tuple[dict, ...]:

        """从数据访问层获得数据模型实例

        传入主键值或者其他字段键值对作为等值筛选器从数据访问层查询符合的原始记录。

        特性
        ^^^^^^

        - 无结果时返回空元组
        """
        return ()  # TODO

    @classmethod
    async def from_fetch(cls, /, _id: BusinessSchemeIDType, _dao = None, **kwargs):

        """从数据访问层获得数据模型实例

        传入主键值或者其他字段键值对作为等值筛选器从数据访问层查询符合的记录并实例化本数据模型。

        特性
        ^^^^^^

        - 只能实例化一个符合条件的数据模型，有多个结果或无结果会报错
        """
        res = await cls.simple_fetch(_id, **kwargs)

        if len(res) > 1:
            raise ValueError('Multiple records found.')  # TODO a better report
        elif len(res) == 0:
            raise ValueError('No record found.')
        else:
            return cls(**res[0])

    @classmethod
    async def from_primary_key(cls, primary_key_value, _dao: DataAccessObject = DataAccessObject.SERV_DAO) -> typing.Self:

        return await _dao.select_a_scheme(
            cls,
            EqFilter(cls.get_primary_key(), primary_key_value)
        )