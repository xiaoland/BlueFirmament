"""DataAccessLayer Moule Base
"""

__all__ = [
    'DataAccessLayer',
    'TableLikeDataAccessLayer',
    'KVLikeDataAccessLayer',
    'QueueLikeDataAccessLayer',
    'DataAccessObject', 
    'DataAccessObjects'
]

import abc
import typing
from typing import Optional as Opt
from .types import DALPath, FilterLikeType, StrictDALPath, FieldLikeType
from .filters import LimitModifier
from ..utils import dump_enum
from .._types import Undefined, _undefined

if typing.TYPE_CHECKING:
    from ..auth import AuthSession
    from ..scheme.field import Field, FieldValueProxy
    from blue_firmament.task.context import ExtendedTaskContext


SchemeTV = typing.TypeVar('SchemeTV', bound="BaseScheme")
FieldValueTV = typing.TypeVar('FieldValueTV')
class DataAccessLayer(abc.ABC):

    '''碧霄数据访问对象基类

    一个DAL实例负责对一个数据源的操作

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

    异常
    -----
    - 令牌过期无法访问数据，抛出 :meth:`exceptions.Unauthorized`
    '''

    def __init__(self, 
        session: "AuthSession"
    ) -> None:
        self._session = session

    def __init_subclass__(
        cls,
        default_path: Opt[StrictDALPath] = None
    ) -> None:
        if default_path is not None:
            cls.__default_path = default_path

    def dump_path(self, path: Opt[DALPath]) -> StrictDALPath:

        '''序列化路径为严格路径
        '''
        if path is None:
            return self.__default_path

        return StrictDALPath(tuple(
            dump_enum(i) if i is not None else j 
            for i, j in zip(path, self.__default_path)
        ))


class TableLikeDataAccessLayer(DataAccessLayer):

    @typing.overload
    @abc.abstractmethod
    async def insert(self,
        to_insert: dict,
        path: Opt[DALPath] = None,
        exclude_key: bool = True,
    ) -> dict:
        pass

    @typing.overload
    @abc.abstractmethod
    async def insert(self,
        to_insert: SchemeTV,
        path: Opt[DALPath] = None,
        exclude_key: bool = True,
    ) -> SchemeTV:
        pass

    @abc.abstractmethod
    async def insert(self,
        to_insert: dict | SchemeTV,
        path: Opt[DALPath] = None,
        exclude_key: bool = True,
    ) -> dict | SchemeTV:
        '''插入

        :param to_insert: 要插入的数据，可以是字典、数据模型实例
        :param path: 路径；如果未提供且要插入的数据是数据模型实例，则使用数据模型提供的路径信息
        :param exclude_key: 是否排除键；默认开启
            在数据库自动生成主键的场景下很有用
        '''

    @abc.abstractmethod
    async def delete(self,
        to_delete: SchemeTV | typing.Type[SchemeTV],
        *filters: FilterLikeType,
        path: Opt[DALPath] = None,
    ) -> None:
        
        """删除
        
        :param to_delete: 要删除的数据，可以是数据模型实例或数据模型类
        :param *filters: 筛选器列表（同时作用）；更多详情见下面
        :param path: 路径；如果不提供且要删除的数据是数据模型，则使用数据模型提供的路径信息
        """

    @typing.overload
    @abc.abstractmethod
    async def update(self,
        to_update: SchemeTV,
        *filters: FilterLikeType,
        path: Opt[DALPath] = None,
        only_dirty: bool = True,
        exclude_key: bool = True,
    ) -> SchemeTV:
        ...

    @typing.overload
    @abc.abstractmethod
    async def update(self,
        to_update: dict,
        *filters: FilterLikeType,
        path: Opt[DALPath] = None,
        only_dirty: bool = True,
        exclude_key: bool = True,
    ) -> dict:
        ...

    @typing.overload
    @abc.abstractmethod
    async def update(self,
        to_update: "FieldValueProxy[FieldValueTV]" | FieldValueTV,
        *filters: FilterLikeType,
        path: Opt[DALPath] = None,
        only_dirty: bool = True,
        exclude_key: bool = True,
    ) -> FieldValueTV:
        ...

    @typing.overload
    @abc.abstractmethod
    async def update(self,
        to_update: typing.Tuple["Field[FieldValueTV]", FieldValueTV],
        *filters: FilterLikeType,
        path: Opt[DALPath] = None,
        only_dirty: bool = True,
        exclude_key: bool = True,
    ) -> FieldValueTV:
        ...

    @abc.abstractmethod
    async def update(self,
        to_update: typing.Union[
            dict, SchemeTV,
            "FieldValueProxy[FieldValueTV]",
            FieldValueTV,  # only for type hint
            typing.Tuple["Field[FieldValueTV]", FieldValueTV]
        ],
        *filters: FilterLikeType,
        path: Opt[DALPath] = None,
        only_dirty: bool = True,
        exclude_key: bool = True,
    ) -> typing.Union[
            dict, 
            SchemeTV, 
            FieldValueTV,
        ]:

        '''更新

        只支持更新单例

        :param to_update: 要更新的数据

            可以是字典、数据模型实例、字段值代理实例 
            （`{}`, `MyScheme.field_a`, `my_scheme.field_a`）
        :param *filters: 筛选器列表（同时作用）；更多详情见下面
        :param path: 路径；更多详情见下面
        :param only_dirty: 是否只更新脏字段；仅当 ``to_update`` 为数据模型实例时有效
        :param exclude_key:
        :raises UpdateFailure: 更新失败
        
        :returns: 

            - 如果 `to_update` 为数据模型实例，则返回更新后的数据模型实例 
            - 如果 `to_update` 为字段值代理实例，则返回更新后的字段值 
            - 如果 `to_update` 为字典，则返回受到更新的整个记录（字典格式）

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

    # TODO update that returns all affected records

    @typing.overload
    @abc.abstractmethod
    async def select(self,
        to_select: typing.Type[SchemeTV],
        *filters: FilterLikeType,
        path: Opt[DALPath] = None,
        task_context: Opt["ExtendedTaskContext"] = None,
    ) -> typing.Tuple[SchemeTV, ...]:
        pass

    @typing.overload
    @abc.abstractmethod
    async def select(self,
        to_select: "Field[FieldValueTV]",
        *filters: FilterLikeType,
        path: Opt[DALPath] = None,
        task_context: Opt["ExtendedTaskContext"] = None,
    ) -> typing.Tuple[FieldValueTV, ...]:
        pass

    @typing.overload
    @abc.abstractmethod 
    async def select(self,
        to_select: typing.Iterable[FieldLikeType],
        *filters: FilterLikeType,  # 实际上此时 str, int 不支持
        path: Opt[DALPath] = None,
        task_context: Opt["ExtendedTaskContext"] = None,
    ) -> typing.Tuple[dict, ...]:
        pass

    @abc.abstractmethod
    async def select(self,
        to_select: typing.Union[
            typing.Type[SchemeTV], 
            "Field[FieldValueTV]",
            typing.Iterable[FieldLikeType],
        ],
        *filters: FilterLikeType,
        path: Opt[DALPath] = None,
        task_context: Opt["ExtendedTaskContext"] = None,
    ) -> typing.Union[
            typing.Tuple[SchemeTV, ...],
            typing.Tuple[FieldValueTV, ...],
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
        to_select: typing.Type[SchemeTV],
        *filters: FilterLikeType,
        path: Opt[DALPath] = None,
        task_context: Opt["ExtendedTaskContext"] = None,
    ) -> SchemeTV:
        ...

    @typing.overload
    async def select_one(self,
        to_select: "Field[FieldValueTV]",
        *filters: FilterLikeType,
        path: Opt[DALPath] = None,
        task_context: Opt["ExtendedTaskContext"] = None,
    ) -> FieldValueTV:
        ...

    @typing.overload
    async def select_one(self,
        to_select: typing.Iterable[FieldLikeType],
        *filters: FilterLikeType,
        path: Opt[DALPath] = None,
        task_context: Opt["ExtendedTaskContext"] = None,
    ) -> dict:
        ...

    async def select_one(self,
        to_select: typing.Union[
            typing.Type[SchemeTV], 
            "Field[FieldValueTV]",
            typing.Iterable[FieldLikeType],
        ],
        *filters: FilterLikeType,
        path: Opt[DALPath] = None,
        task_context: Opt["ExtendedTaskContext"] = None,
    ) -> typing.Union[
        SchemeTV,
        FieldValueTV,
        dict
    ]:

        '''查询单个记录

        添加一个 LimitFilter(1)
        '''

        return (await self.select(
            to_select,
            *filters, LimitModifier(1),
            path=path,
            task_context=task_context
        ))[0]

    @abc.abstractmethod
    async def upsert(self):  # TODO
        pass


class KVLikeDataAccessLayer(DataAccessLayer):

    @abc.abstractmethod
    async def get(self, key: str) -> Opt[typing.Any]:
        ...

    @abc.abstractmethod
    async def set(self, key: str, value: typing.Any) -> None:
        ...

class QueueLikeDataAccessLayer(DataAccessLayer):

    @abc.abstractmethod
    async def push(self, queue: str, item: typing.Any) -> None:
        """Push an item to the head of the queue.
        """
        ...

    @abc.abstractmethod
    async def pop(self, queue: str) -> typing.Any:
        """Pop the first item of the queue.
        """
        ...

    def try_pop(self, queue: str) -> Opt[typing.Any]:
        try:
            return self.pop(queue)
        except Exception:
            return None

    @abc.abstractmethod
    def pop_and_push(self, queue: str, dst_queue: str) -> typing.Any:
        """Pop an item and then push it to another queue.
        """

    def try_pop_and_push(self, queue: str, dst_queue: str) -> Opt[typing.Any]:
        try:
            return self.pop_and_push(queue, dst_queue)
        except Exception:
            return None

    @abc.abstractmethod
    def blocking_pop_and_push(
        self,
        queue: str,
        dst_queue: str,
        timeout: float = 0
    ) -> typing.Any:
        """Pop and push an item to another queue,
        blocking until an item is available.
        """


class DataAccessObject(
    typing.Generic[SchemeTV]
):
    
    def __init__(self, 
        dal: DataAccessLayer,
        scheme_cls: typing.Type[SchemeTV],
    ) -> None:
        self.__dal = dal
        self.__scheme_cls = scheme_cls

    def select(self,
        *filters: FilterLikeType,
        task_context: Opt["ExtendedTaskContext"] = None,
    ):
        return self.__dal.select(  
            to_select=self.__scheme_cls,
            *filters,
            task_context=task_context
        )
        
    def select_fields(self,
        to_select: typing.Iterable[FieldLikeType],
        *filters: FilterLikeType,
        task_context: Opt["ExtendedTaskContext"] = None,
    ):
        return self.__dal.select(  
            to_select=to_select,
            *filters,
            task_context=task_context
        ) 
        
    def select_field(self,
        to_select: "Field[FieldValueTV]",
        *filters: FilterLikeType,
        task_context: Opt["ExtendedTaskContext"] = None,
    ):
        return self.__dal.select(  
            to_select=to_select,
            *filters,
            task_context=task_context
        ) 

    def select_one(self, 
        *filters: FilterLikeType,
        task_context: Opt["ExtendedTaskContext"] = None,
    ):
        return self.__dal.select_one(
            to_select=self.__scheme_cls,
            *filters,
            task_context=task_context
        ) 
        
    def select_a_field(self, 
        to_select: "Field[FieldValueTV]",
        *filters: FilterLikeType,
        task_context: Opt["ExtendedTaskContext"] = None,
    ):
        return self.__dal.select_one(
            to_select=to_select,
            *filters,
            task_context=task_context
        )
    
    def insert(self, 
        to_insert: SchemeTV,
        exclude_key: bool = True,
    ):
        return self.__dal.insert(
            to_insert=to_insert, 
            exclude_key=exclude_key
        )
    
    @typing.overload
    async def update(self,
        to_update: SchemeTV,
        *filters: FilterLikeType,
        only_dirty: bool = True,
        exclude_key: bool = True,
    ) -> SchemeTV:
        ...

    @typing.overload
    async def update(self,
        to_update: FieldValueTV,
        *filters: FilterLikeType,
        only_dirty: bool = True,
        exclude_key: bool = True,
    ) -> FieldValueTV:
        ...

    @typing.overload
    async def update(self,
        to_update: typing.Tuple["Field[FieldValueTV]", FieldValueTV],
        *filters: FilterLikeType,
        only_dirty: bool = True,
        exclude_key: bool = True,
    ) -> FieldValueTV:
        ...
    
    def update(self,
        to_update: typing.Union[
            SchemeTV,
            FieldValueTV,
            typing.Tuple["Field[FieldValueTV]", FieldValueTV]
        ],
        *filters: FilterLikeType,
        only_dirty: bool = True,
        exclude_key: bool = True,
    ):
        return self.__dal.update(
            to_update=to_update,
            *filters,
            only_dirty=only_dirty,
            exclude_key=exclude_key
        )
    
    def delete(self, 
        to_delete: Opt[SchemeTV] = None, 
        *filters: FilterLikeType
    ):
        return self.__dal.delete(
            to_delete=to_delete or self.__scheme_cls,
            *filters
        )


class DataAccessObjects:

    def __init__(self,
        session: "AuthSession"
    ) -> None:
        self.__session = session
        self.__dals: dict[typing.Type[DataAccessLayer], DataAccessLayer] = {}

    def __call__(self, scheme_cls: typing.Type[SchemeTV]) -> DataAccessObject[SchemeTV]:
        if scheme_cls.__dal__ is None:
            raise ValueError("scheme don't has a dal")
        try:
            dal = self.__dals[scheme_cls.__dal__]
        except KeyError:
            dal = scheme_cls.__dal__(session=self.__session)
            self.__dals[scheme_cls.__dal__] = dal
        
        return DataAccessObject(
            dal=dal, scheme_cls=scheme_cls
        )