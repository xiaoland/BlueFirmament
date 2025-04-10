"""Data Access Layer (DAL) of Blue Firmament"""

import typing
import abc
import enum
from ..utils import dump_enum
from .filters import *
from .exceptions import *

if typing.TYPE_CHECKING:
    from ..scheme import BaseScheme


DALPath = typing.NewType('DALPath', typing.Tuple[str | enum.Enum | None, ...])
'''数据访问路径'''
StrictDALPath = typing.NewType('StrictDALPath', typing.Tuple[str, ...])
'''严格数据访问路径（只可以为字符串条目）'''


class DataAccessObject(abc.ABC):

    '''碧霄数据访问对象基类

    一个DAO实例负责对一个数据源的操作

    关键概念
    ----------
    DALPath
    ^^^^^^^^
    数据访问路径

    路径是倒序的，从小到大

    由不定长的路径条目组成，路径条目可以是字符串、枚举值或None
    - 如果路径条目是枚举，会被序列化为字符串
    - 如果路径条目是None，会被默认值取代（DAO配置的默认DALPath按位置合并）

    对于一个DAO类来说，路径长度是固定的，但用户不需要提供完整的路径（短于完整路径），比如：
    ```python
    class MyDAO(DataAccessObject):
        def __init__(self):
            super().__init__(DALPath(('default_table', 'default_schema')))

    dao = MyDAO()
    dao.insert(path=DALPath(('another_table',)))  # 插入到 default_schema.default_table
    ```
    '''

    SERV_DAO: 'DataAccessObject' = None  # type: ignore[assignment]
    '''服务角色数据访问对象（全局实例）'''
    ANON_DAO: 'DataAccessObject' = None  # type: ignore[assignment]
    '''匿名角色数据访问对象（全局实例）'''

    def __init__(self, default_path: StrictDALPath) -> None:

        '''
        :param default_path: 默认路径；将作为完整路径（不可以有None条目）
        '''
        
        self.__default_path = default_path
        '''默认路径'''

    def dump_path(self, path: typing.Optional[DALPath]) -> StrictDALPath:

        '''序列化路径为严格路径
        '''
        if path is None:
            return self.__default_path

        return StrictDALPath(tuple(
            dump_enum(i) if i is not None else j for i, j in zip(path, self.__default_path)
        ))

    @typing.overload
    @abc.abstractmethod
    async def insert(self,
        to_insert: dict, 
        path: typing.Optional[DALPath] = None,
    ) -> dict:
        pass

    @typing.overload
    @abc.abstractmethod
    async def insert(self,
        to_insert: "BaseScheme",
        path: typing.Optional[DALPath] = None,
    ) -> "BaseScheme":
        pass

    @typing.overload
    @abc.abstractmethod
    async def insert(self,
        to_insert: typing.List["dict | BaseScheme"],
        path: typing.Optional[DALPath] = None,
    ) -> typing.List["dict | BaseScheme"]:
        pass

    TO_INSERT_TYPE = typing.TypeVar('TO_INSERT_TYPE', bound=(
        typing.Union[
            dict, "BaseScheme", 
            typing.List["dict | BaseScheme"]
        ]
    ))
    @abc.abstractmethod
    async def insert(self,
        to_insert: TO_INSERT_TYPE,
        path: typing.Optional[DALPath] = None,
    ) -> TO_INSERT_TYPE:
        
        '''插入
        
        :param to_insert: 要插入的数据，可以是字典、数据模型实例或它们的可迭代集合
        :param path: 路径；更多详情见下面

        Behaviour
        ---------
        如果插入的数据是关于数据模型实例的列表，会根据数据模型的主键来分配实例化插入结果 \n
        举例说返回结果是字典的列表，此时就需要找到哪个字典对应哪个数据模型

        不提供路径
        ^^^^^^^^^^
        - 如果要插入的数据是数据模型实例，则使用数据模型提供的路径信息
        '''

    @abc.abstractmethod
    async def delete(self,
        *filters: DALFilter,
        path: typing.Optional[DALPath] = None,
    ) -> None:
        pass

    async def delete_a_scheme(self, scheme: typing.Type["BaseScheme"], primary_key_value):

        '''删除一个数据模型实例
        '''
        return await self.delete(
            EqFilter(scheme.get_primary_key(), primary_key_value),
            path=DALPath((scheme.__table_name__, scheme.__schema_name__)),
        )
    
    @typing.overload
    @abc.abstractmethod
    async def update(self,
        to_update: "BaseScheme",
        path: typing.Optional[DALPath] = None,
        /,
        *filters: DALFilter,
    ) -> "BaseScheme":
        ...

    @typing.overload
    @abc.abstractmethod
    async def update(self,
        to_update: dict,
        path: typing.Optional[DALPath] = None,
        /,
        *filters: DALFilter,
    ) -> dict:
        ...

    @abc.abstractmethod
    async def update(self,
        to_update: "dict | BaseScheme",
        path: typing.Optional[DALPath] = None,
        /,
        *filters: DALFilter,
    ) -> "dict | BaseScheme":
        
        '''更新
        
        :param to_update: 要更新的数据，可以是字典或数据模型实例
        :param path: 路径；更多详情见下面
        :param *filters: 筛选器列表（同时作用）；更多详情见下面

        Behaviour
        ---------

        不提供筛选器
        ^^^^^^^^^^^^^
        默认情况下，必须提供至少一个筛选器才能执行更新的操作，
        但如果待更新的数据是数据模型实例，则此时会使用 ``EqFilter(数据模型的主键) ``作为筛选器
        '''

    @abc.abstractmethod
    async def select(self,
        *filters: DALFilter,
        path: typing.Optional[DALPath] = None,
        fields: typing.Optional[typing.Iterable[str | enum.Enum]] = None,
    ) -> typing.Tuple[dict, ...]:
        
        '''查询

        :param path: 数据访问路径；如果不提供则使用默认路径
        :param *filters: 筛选器列表（同时作用）
        :param fields: 要查询的字段列表；如果不提供则查询路径目标的所有字段

        :returns: 查询结果列表；每个结果是一个字典，包含字段名和对应的值

        Behaviour
        ----------
        - 找不到数据时报错 ``NotFound``
        '''
        pass

    SELECT_SCHEME_TYPE = typing.TypeVar('SELECT_SCHEME_TYPE', bound="BaseScheme")
    async def select_a_scheme(self,
        scheme: typing.Type[SELECT_SCHEME_TYPE],
        *filters: DALFilter
    ) -> SELECT_SCHEME_TYPE:
        
        '''获取单个数据模型实例

        :param scheme: 数据模型类
        :param *filters: 筛选器列表（同时作用）

        Behaviour
        ----------
        - 根据筛选器以及模型类提供的路径信息从数据源中获取数据并序列化为数据模型实例
        - 如果有多个记录符合条件则抛出异常 ``DuplicateRecord``
        '''
        res = await self.select(
            *filters, SingleFilter(),
            path=DALPath((scheme.__table_name__, scheme.__schema_name__)),
        )

        return scheme(**res[0])

    async def select_a_scheme_from_primary_key(self,
        scheme: typing.Type[SELECT_SCHEME_TYPE],
        primary_key_value,
    ) -> SELECT_SCHEME_TYPE:
        
        '''通过主键获取单个数据模型实例
        '''
        return await self.select_a_scheme(
            scheme, EqFilter(scheme.get_primary_key(), primary_key_value)
        )

    @abc.abstractmethod
    async def upsert(self):  # TODO
        pass


def set_serv_dao(dao: DataAccessObject, dao_cls: typing.Type[DataAccessObject]) -> None:
    
    '''设置服务角色数据访问对象（全局实例）
    '''
    dao_cls.SERV_DAO = dao

def set_anon_dao(dao: DataAccessObject, dao_cls: typing.Type[DataAccessObject]) -> None:
        
    '''设置匿名角色数据访问对象（全局实例）
    '''
    dao_cls.ANON_DAO = dao
