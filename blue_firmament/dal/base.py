"""DataAccessLayer Moule Base
"""

__all__ = [
    'DataAccessLayer',
    'DataAccessLayerWithAuth',
    'TableLikeDataAccessLayer',
    'KVLikeDataAccessLayer',
    'QueueLikeDataAccessLayer',
    'PubSubMessage',
    'PubSubLikeDataAccessLayer',
    'DataAccessObject', 
    'DataAccessObjects'
]

import abc
import typing
from typing import Annotated as Anno, Optional as Opt, Literal as Lit
from .types import DALPath, FilterLikeType, StrictDALPath, FieldLikeType
from .filters import LimitModifier
from ..utils.enum_ import dump_enum
from .._types import Undefined, _undefined

if typing.TYPE_CHECKING:
    from ..auth import AuthSession
    from ..scheme.field import Field, FieldValueProxy, BaseScheme
    from blue_firmament.task.context import ExtendedTaskContext


SchemeTV = typing.TypeVar('SchemeTV', bound="BaseScheme")
FieldValueTV = typing.TypeVar('FieldValueTV')
class DataAccessLayer(abc.ABC):
    """BlueFirmament DataAccessLayer base class.
    """

    def __init_subclass__(
        cls,
        default_path: Opt[StrictDALPath] = None
    ) -> None:
        if default_path is not None:
            cls.__default_path = default_path

    def __init__(self, **kwargs):
        self.__post_init__()

    def __post_init__(self):
        ...

    def dump_path(self, path: Opt[DALPath] = None) -> StrictDALPath:
        """Serialize DALPath to StrictDALPath.

        :returns: StrictDALPath. If `path` is None, returns the default path.
        """
        if path is None:
            return self.__default_path

        return StrictDALPath(tuple(
            dump_enum(i) if i is not None else j 
            for i, j in zip(path, self.__default_path)
        ))

    @property
    def default_path(self) -> StrictDALPath:
        return self.__default_path

class DataAccessLayerWithAuth(DataAccessLayer):

    def __init__(self, auth_session: "AuthSession", **kwargs):
        self._auth_session = auth_session
        super().__init__()

class TableLikeDataAccessLayer(DataAccessLayer):

    @typing.overload
    @abc.abstractmethod
    async def insert(
        self,
        to_insert: dict,
        path: Opt[DALPath] = None,
        exclude_natural_key: bool = True,
    ) -> dict:
        ...
    @typing.overload
    @abc.abstractmethod
    async def insert(
        self,
        to_insert: SchemeTV,
        path: Opt[DALPath] = None,
        exclude_natural_key: bool = True,
    ) -> SchemeTV:
        ...
    @abc.abstractmethod
    async def insert(
        self,
        to_insert: dict | SchemeTV,
        path: Opt[DALPath] = None,
        exclude_natural_key: bool = True,
    ) -> dict | SchemeTV:
        """Insert a row.

        :param to_insert:
            Data to insert. Can be a dict, model.
        :param path: DALPath.
            Use the model DALPath when None.
        :param exclude_natural_key:
            Exclude natural key fields of the model, defaults to True.

        :returns:
            The inserted row, same type as `to_insert`.
            If `to_insert` is a model, its private fields will be kept.
        """

    @abc.abstractmethod
    async def delete(self,
        to_delete: SchemeTV | typing.Type[SchemeTV],
        *filters: FilterLikeType,
        path: Opt[DALPath] = None,
    ) -> None:
        """Delete a row.
        
        :param to_delete: a data model instance or a data model class.
        :param filters: filter out rows to be deleted.
            If `to_delete` is a data model instance,
            its primary key will be used as a filter when no filter provided.
        :param path: DALPath.
            Use the data model DALPath when None.
        """

    @typing.overload
    @abc.abstractmethod
    async def update(
        self,
        to_update: SchemeTV,
        *filters: FilterLikeType,
        path: Opt[DALPath] = None,
        only_dirty: bool = True,
        exclude_key: bool = True,
    ) -> SchemeTV:
        ...
    @typing.overload
    @abc.abstractmethod
    async def update(
        self,
        to_update: dict,
        *filters: FilterLikeType,
        path: Opt[DALPath] = None,
        only_dirty: bool = True,
        exclude_key: bool = True,
    ) -> dict:
        ...
    @typing.overload
    @abc.abstractmethod
    async def update(
        self,
        to_update: "FieldValueProxy[FieldValueTV]" | FieldValueTV,
        *filters: FilterLikeType,
        path: Opt[DALPath] = None,
        only_dirty: bool = True,
        exclude_key: bool = True,
    ) -> FieldValueTV:
        ...
    @typing.overload
    @abc.abstractmethod
    async def update(
        self,
        to_update: typing.Tuple["Field[FieldValueTV]", FieldValueTV],
        *filters: FilterLikeType,
        path: Opt[DALPath] = None,
        only_dirty: bool = True,
        exclude_key: bool = True,
    ) -> FieldValueTV:
        ...
    @abc.abstractmethod
    async def update(
        self,
        to_update: typing.Union[
            dict, SchemeTV,
            "FieldValueProxy[FieldValueTV]",
            FieldValueTV,  # only for type hint
            typing.Tuple["Field[FieldValueTV]", FieldValueTV]
        ],
        *filters: FilterLikeType,
        path: Opt[DALPath] = None,
        only_dirty: bool = True,
        exclude_natural_key: bool = True,
    ) -> typing.Union[
        dict,
        SchemeTV,
        FieldValueTV,
    ]:
        """Update a row.

        :param to_update: New data.
            Can be:
            - a dict `{'field_a': 2}`
            - data model instance `MyScheme(field_a=2)`
            - a field value proxy instance `MyScheme.field_a`
            - field and its value `(MyScheme.field_a, 2)`
        :param filters:
            Filter out the rows to apply `to_update`.
            Al least one filter must be provided.

            If `to_update` is a data model instance,
            its primary key will be used as a filter when no filter provided.
        :param path: DALPath.
        :param only_dirty: Update only the dirty fields of the data model.
        :param exclude_natural_key: Exclude natural key fields of the model, defaults to True.
        :raises UpdateFailure: 更新失败
        :returns: The updated data.
            If `to_update` is a data model, returns row in data model and keep original
            private fields.
            If `to_update` is field value proxy，returns the new value (without proxy).
            If `to_update` is dict，returns row in dict.
        """

        # TODO returns all affected records

    @typing.overload
    @abc.abstractmethod
    async def select(
        self,
        to_select: typing.Type[SchemeTV],
        *filters: FilterLikeType,
        path: Opt[DALPath] = None,
        task_context: Opt["ExtendedTaskContext"] = None,
    ) -> typing.Tuple[SchemeTV, ...]:
        ...
    @typing.overload
    @abc.abstractmethod
    async def select(
        self,
        to_select: "Field[FieldValueTV]",
        *filters: FilterLikeType,
        path: Opt[DALPath] = None,
        task_context: Opt["ExtendedTaskContext"] = None,
    ) -> typing.Tuple[FieldValueTV, ...]:
        ...
    @typing.overload
    @abc.abstractmethod 
    async def select(
        self,
        to_select: typing.Iterable[FieldLikeType],
        *filters: FilterLikeType,  # 实际上此时 str, int 不支持
        path: Opt[DALPath] = None,
        task_context: Opt["ExtendedTaskContext"] = None,
    ) -> typing.Tuple[dict, ...]:
        ...
    @abc.abstractmethod
    async def select(
        self,
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
        """Select rows.

        :param to_select: Field(s) to select.
            Can be a data model class, field-like(s).

            If `to_select` is a data model class, all fields of the data model will be selected.
        :param filters: Filter out rows to be selected.
            If str, int, an EqFilter of the primary key or field will be created.
        :param path: DALPath.
            If `to_select` is field，use its data model's DAL path.
        :param task_context:
            Task Context injected into return when `to_select` is a data model.
        :raises NotFound: Not a row selected.
        :returns: Selected rows.
            If `to_select` is data model，returns a tuple of data model instances.
            If `to_select` is a field, returns a tuple of field values.
            In other cases, returns a tuple of dicts.

        Examples
        --------
        >>> dao.select(MyScheme, 'primary key value').limit(1)
        # get a MyScheme instance where primary key equals 'primary key value'
        >>> dao.select(MyScheme.field_a, 'primary key value').one()
        # get MySchem.field_a's value using primary key
        >>> dao.select(MyScheme, MyScheme.field_a.equals(value))
        # Get MyScheme using EqFilter on fields other than primary key
        """
        ...

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

    def __init_subclass__(
        cls,
        queue_name: Opt[str] = None,
        **kwargs
    ):
        cls.__queue_name__ = queue_name

        super().__init_subclass__(**kwargs)

    @abc.abstractmethod
    async def push(self, item: bytes) -> None:
        """Push an item to the head of the queue.
        """
        ...

    @abc.abstractmethod
    async def pop(self, wait: bool = True) -> bytes:
        """Pop the first item of the queue.

        :param wait: Blocks until an item is available.
        """
        ...


class PubSubMessage(typing.TypedDict):
    channel: str
    data: bytes

class PubSubLikeDataAccessLayer(DataAccessLayer):
    """

    :cvar __channel_name__: Publish or subscribe to this channel.
    """

    def __init_subclass__(
        cls,
        channel_name: Opt[str] = None,
        **kwargs
    ):
        cls.__channel_name__ = channel_name

        super().__init_subclass__(**kwargs)

    @abc.abstractmethod
    async def publish(self, item: bytes, *channel_names: str) -> None:
        """Publish a message to channel(s).

        :param item: The message to publish.
        :param channel_names: Channel names.
            If not provided, the channel_name configured in class level will be used.
        """
        ...

    @abc.abstractmethod
    async def subscribe(self, *channel_names: str) -> None:
        """Subscribe to these channels.

        :param channel_names: Channel names.
            If not provided, the channel_name configured in class level will be used.
        """
        ...

    @abc.abstractmethod
    async def unsubscribe(self, *channel_names: str) -> None:
        """Unsubscribe from these channels.

        :param channel_names: Channel names.
            If not provided, the channel_name configured in class level will be used.
        """
        ...

    @abc.abstractmethod
    async def get_message(self, timeout: int = 0) -> PubSubMessage:
        """Get a message on subscribed channels. (block until a message is received)
        """
        ...

    async def listen(self, timeout: int = 0) -> typing.AsyncIterator[PubSubMessage]:
        """Listen to messages on subscribed channels.
        """
        while True:
            message = await self.get_message(timeout=timeout)
            yield message


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
        if not isinstance(self.__dal, TableLikeDataAccessLayer):
            raise TypeError(f"{self.__dal.__name__} not support TableLike operation")
        return self.__dal.select(
            self.__scheme_cls,
            *filters,
            task_context=task_context
        )
        
    def select_fields(self,
        to_select: typing.Iterable[FieldLikeType],
        *filters: FilterLikeType,
        task_context: Opt["ExtendedTaskContext"] = None,
    ):
        if not isinstance(self.__dal, TableLikeDataAccessLayer):
            raise TypeError(f"{self.__dal.__name__} not support TableLike operation")
        return self.__dal.select(  
            to_select,
            *filters,
            task_context=task_context
        ) 
        
    def select_field(self,
        to_select: "Field[FieldValueTV]",
        *filters: FilterLikeType,
        task_context: Opt["ExtendedTaskContext"] = None,
    ):
        if not isinstance(self.__dal, TableLikeDataAccessLayer):
            raise TypeError(f"{self.__dal.__name__} not support TableLike operation")
        return self.__dal.select(  
            to_select,
            *filters,
            task_context=task_context
        ) 

    def select_one(self, 
        *filters: FilterLikeType,
        task_context: Opt["ExtendedTaskContext"] = None,
    ):
        if not isinstance(self.__dal, TableLikeDataAccessLayer):
            raise TypeError(f"{self.__dal.__name__} not support TableLike operation")
        return self.__dal.select_one(
            self.__scheme_cls,
            *filters,
            task_context=task_context
        ) 
        
    def select_a_field(self, 
        to_select: "Field[FieldValueTV]",
        *filters: FilterLikeType,
        task_context: Opt["ExtendedTaskContext"] = None,
    ):
        if not isinstance(self.__dal, TableLikeDataAccessLayer):
            raise TypeError(f"{self.__dal.__name__} not support TableLike operation")
        return self.__dal.select_one(
            to_select,
            *filters,
            task_context=task_context
        )
    
    def insert(self, 
        to_insert: SchemeTV,
        exclude_natural_key: bool = True,
    ):
        if not isinstance(self.__dal, TableLikeDataAccessLayer):
            raise TypeError(f"{self.__dal.__name__} not support TableLike operation")
        return self.__dal.insert(
            to_insert=to_insert, 
            exclude_natural_key=exclude_natural_key
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
        if not isinstance(self.__dal, TableLikeDataAccessLayer):
            raise TypeError(f"{self.__dal.__name__} not support TableLike operation")
        return self.__dal.update(
            to_update,
            *filters,
            only_dirty=only_dirty,
            exclude_key=exclude_key
        )
    
    def delete(self, 
        to_delete: Opt[SchemeTV] = None, 
        *filters: FilterLikeType
    ):
        if not isinstance(self.__dal, TableLikeDataAccessLayer):
            raise TypeError(f"{self.__dal.__name__} not support TableLike operation")
        return self.__dal.delete(
            to_delete or self.__scheme_cls,
            *filters
        )


class DataAccessObjects:

    def __init__(
        self,
        auth_session: "AuthSession"
    ) -> None:
        self.__auth_session = auth_session
        self.__dals: dict[type[DataAccessLayer], DataAccessLayer] = {}

    def __call__(self, scheme_cls: typing.Type[SchemeTV]) -> DataAccessObject[SchemeTV]:
        if scheme_cls.__dal__ is None:
            raise ValueError(f"scheme {scheme_cls.__name__} not configured a DAL class")
        
        dal = self.__dals.setdefault(
            scheme_cls.__dal__, 
            scheme_cls.__dal__(auth_session=self.__auth_session)
        )
        
        return DataAccessObject(
            dal=dal, scheme_cls=scheme_cls
        )

    def is_expired(self) -> bool:
        """Session expired is seen as DAOs expired,"""
        return self.__auth_session.is_expired()