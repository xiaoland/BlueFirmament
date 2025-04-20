
from .filters import *
from .exceptions import *
from . import DALPath, FilterLikeType, StrictDALPath, FieldLikeType
from .filters import DALFilter, LimitFilter
from ..utils import dump_enum
import abc
import typing
from typing import Optional as Opt

if typing.TYPE_CHECKING:
    from ..scheme import BaseScheme
    from ..scheme.field import BlueFirmamentField, FieldValueProxy


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

    数据类型映射
    ----------
    - 数组(Array), JSONB 数组, -> list
    - JSONB 对象 -> dict
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

    def dump_path(self, path: Opt[DALPath]) -> StrictDALPath:

        '''序列化路径为严格路径
        '''
        if path is None:
            return self.__default_path

        return StrictDALPath(tuple(
            dump_enum(i) if i is not None else j for i, j in zip(path, self.__default_path)
        ))

    BaseSchemeType = typing.TypeVar('BaseSchemeType', bound="BaseScheme")
    FieldValueType = typing.TypeVar('FieldValueType')

    @typing.overload
    @abc.abstractmethod
    async def insert(self,
        to_insert: dict,
        path: Opt[DALPath] = None,
    ) -> dict:
        pass

    @typing.overload
    @abc.abstractmethod
    async def insert(self,
        to_insert: BaseSchemeType,
        path: Opt[DALPath] = None,
    ) -> BaseSchemeType:
        pass

    @abc.abstractmethod
    async def insert(self,
        to_insert: dict| BaseSchemeType,
        path: Opt[DALPath] = None,
    ) -> dict | BaseSchemeType:

        '''插入

        :param to_insert: 要插入的数据，可以是字典、数据模型实例
        :param path: 路径；如果未提供且要插入的数据是数据模型实例，则使用数据模型提供的路径信息
        '''

    @abc.abstractmethod
    async def delete(self,
        to_delete: BaseSchemeType | typing.Type[BaseSchemeType],
        *filters: FilterLikeType,
        path: Opt[DALPath] = None,
    ) -> None:
        
        """删除
        
        :param to_delete: 要删除的数据，可以是数据模型实例或数据模型类
        :param *filters: 筛选器列表（同时作用）；更多详情见下面
        :param path: 路径；如果不提供且要删除的数据是数据模型，则使用数据模型提供的路径信息
        """

    DictType = typing.TypeVar('DictType', bound=dict)

    @typing.overload
    @abc.abstractmethod
    async def update(self,
        to_update: BaseSchemeType,
        *filters: DALFilter,
        path: Opt[DALPath] = None,
        only_dirty: bool = True,
    ) -> BaseSchemeType:
        ...

    @typing.overload
    @abc.abstractmethod
    async def update(self,
        to_update: DictType,
        *filters: DALFilter,
        path: Opt[DALPath] = None,
        only_dirty: bool = True,
    ) -> DictType:
        ...

    @typing.overload
    @abc.abstractmethod
    async def update(self,
        to_update: "FieldValueProxy[FieldValueType]" | FieldValueType,
        *filters: DALFilter,
        path: Opt[DALPath] = None,
        only_dirty: bool = True,
    ) -> FieldValueType:
        ...

    @abc.abstractmethod
    async def update(self,
        to_update: typing.Union[
            DictType, BaseSchemeType,
            "FieldValueProxy[FieldValueType]",
            FieldValueType  # only for type hint
        ],
        *filters: DALFilter,
        path: Opt[DALPath] = None,
        only_dirty: bool = True,
    ) -> typing.Union[
            DictType, BaseSchemeType, FieldValueType,
        ]:

        '''更新

        :param to_update: 要更新的数据，\n
            可以是字典、数据模型实例、字段值代理实例 \n
            `{}`, `MyScheme.field_a`, `my_scheme.field_a`
        :param *filters: 筛选器列表（同时作用）；更多详情见下面
        :param path: 路径；更多详情见下面
        :param only_dirty: 是否只更新脏字段；仅当 ``to_update`` 为数据模型实例时有效
        :raises UpdateFailure: 更新失败

        Behaviour
        ---------
        要更新的数据
        ^^^^^^^^^^^^^
        - 为数据模型实例时，调用数据模型的序列化为字典方法（携带 `only_dirty` 参数） 
            - TODO 更新完成后，会清空脏字段
        - 为字段值代理对象时，用其字段名称作为键，被代理对象作为方法

        不提供路径
        ^^^^^^^^^^
        - 在 ``to_update`` 为数据模型实例时，使用数据模型实例的路径
        - 在 ``to_update`` 为字段值代理对象时，使用其数据模型实例的路径
        - 在 ``to_update`` 为字典时，使用默认路径

        不提供筛选器
        ^^^^^^^^^^^^^
        默认情况下，必须提供至少一个筛选器才能执行更新的操作 \n
        但如果 `to_update` 是数据模型实例，则使用实例的主键作为筛选器 \n

        '''

    @typing.overload
    @abc.abstractmethod
    async def select(self,
        to_select: typing.Type[BaseSchemeType],
        *filters: FilterLikeType,
        path: Opt[DALPath] = None,
    ) -> typing.Tuple[BaseSchemeType, ...]:
        pass

    @typing.overload
    @abc.abstractmethod
    async def select(self,
        to_select: "BlueFirmamentField[FieldValueType]",
        *filters: FilterLikeType,
        path: Opt[DALPath] = None,
    ) -> typing.Tuple[FieldValueType, ...]:
        pass

    @typing.overload
    @abc.abstractmethod 
    async def select(self,
        to_select: typing.Iterable[FieldLikeType] | None,
        *filters: FilterLikeType,  # 实际上此时 str, int 不支持
        path: Opt[DALPath] = None,
    ) -> typing.Tuple[dict, ...]:
        pass

    @abc.abstractmethod
    async def select(self,
        to_select: typing.Union[
            typing.Type[BaseSchemeType], 
            "BlueFirmamentField[FieldValueType]",
            typing.Iterable[FieldLikeType],
            None
        ],
        *filters: FilterLikeType,
        path: Opt[DALPath] = None,
    ) -> typing.Union[
            typing.Tuple[BaseSchemeType, ...],
            typing.Tuple[FieldValueType, ...],
            typing.Tuple[dict, ...]
        ]:

        '''查询

        :param to_select: 要查询的字段，可以是数据模型实例、字段实例或可作为字段的列表 
            如果类型为数据模型实例，则选择路径下的所有字段，即 `*`
        :param *filters: 筛选器列表（同时作用）  \n
            如果类型为 `str, int` ，会被当做主键值，创建 ``EqFilter`` ；
            但仅在 `to_select` 为数据模型类与字段实例时生效 \n
        :param path: 数据访问路径；如果不提供\n
            在 `to_select` 为数据模型类时，使用数据模型类的 `dal_path`
            如果为 `BlueFirmamentField`，使用其数据模型类的 `dal_path` 
            都不符合则使用默认路径 

        :raises NotFound: 没有找到任何数据时

        :returns: 以尽可能贴合 `to_select` 的类型返回 \n
            如果 `to_select` 为数据模型类，则返回数据模型实例或其元组 \n
            如果 `to_select` 为字段实例，则返回字段值或其元组 \n
            如果 `to_select` 为可作为字段的列表或 None，则返回字典元组 \n

        Examples
        --------
        .. code-block:: python
            dao.select(MyScheme, 'primary key value').limit(1) 
            # get a MyScheme instance where primary key equals 'primary key value'

            dao.select(MyScheme.field_a, 'primary key value').one() 
            # get MySchem.field_a's value using primary key

            dao.select(MyScheme, MyScheme.field_a.equals(value))
            # Get MyScheme using EqFilter on fields other than primary key

        
        '''
        pass

    @typing.overload
    async def select_one(self,
        to_select: typing.Type[BaseSchemeType],
        *filters: FilterLikeType,
        path: Opt[DALPath] = None,
    ) -> BaseSchemeType:
        ...

    @typing.overload
    async def select_one(self,
        to_select: "BlueFirmamentField[FieldValueType]",
        *filters: FilterLikeType,
        path: Opt[DALPath] = None,
    ) -> FieldValueType:
        ...

    @typing.overload
    async def select_one(self,
        to_select: typing.Iterable[FieldLikeType] | None,
        *filters: FilterLikeType,
        path: Opt[DALPath] = None,
    ) -> dict:
        ...

    async def select_one(self,
        to_select: typing.Union[
            typing.Type[BaseSchemeType], 
            "BlueFirmamentField[FieldValueType]",
            typing.Iterable[FieldLikeType],
            None
        ],
        *filters: FilterLikeType,
        path: Opt[DALPath] = None,
    ) -> typing.Union[
        BaseSchemeType,
        FieldValueType,
        dict
    ]:

        '''查询单个记录

        添加一个 LimitFilter(1)
        '''

        return (await self.select(
            to_select,
            *filters, LimitFilter(1),
            path=path
        ))[0]

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