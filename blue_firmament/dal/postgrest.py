"""PostgrestDAL
"""

import postgrest
import enum
from typing import Optional as Opt

from ..task.context import ExtendedTaskContext, SoBaseTC
from ..auth import AuthSession
from ..scheme.converter import SchemeConverter
from .utils import dump_filters_like
from ..exceptions import Unauthorized
from ..utils.typing_ import safe_issubclass
from ..exceptions import NotFound
from ..scheme.field import Field, FieldValueProxy, FieldValueTV
from .filters import *
from .base import TableLikeDataAccessLayer, DataAccessLayerWithAuth
from .. import __version__, __name__ as __package_name__
from .types import (
    DALPath, FieldLikeType, FilterLikeType, StrictDALPath
)
from .filters import DALFilter
from ..utils.main import call_as_sync
from ..utils.enum_ import dump_enum
from ..scheme import BaseScheme, SchemeTV


class PostgrestDAL(TableLikeDataAccessLayer, DataAccessLayerWithAuth):
    """Access data through PostgREST API.

    Examples
    --------
    .. code-block:: python
        from blue_firmament.dal.postgrest import PostgrestDAO

        class SupaAnonPostgrestDAO(PostgrestDAO,
            url=get_supabase_setting().supabase_url,
            apikey=get_supabase_setting().anon_key,
            default_table="profile"
        ):
            pass
    """
    
    def __init_subclass__(
        cls,
        url: str,
        apikey: str,
        default_table: str | enum.Enum,
        default_schema: str | enum.Enum = "public",
        **kwargs
    ) -> None:
        """
        :param apikey: Supabase API Key.
            Use anon key for authenticated or anonymous user,
            use serv key for service_role user.
        """
        cls.__url = url
        cls.__apikey = apikey

        return super().__init_subclass__(
            default_path=StrictDALPath((dump_enum(default_table), dump_enum(default_schema))),
            **kwargs
        )

    def __post_init__(self):
        self._client = postgrest.AsyncPostgrestClient(
            base_url=self.__url,
            schema=dump_enum(self.default_path[1]),
            headers={
                'X-Client-Info': f'{__package_name__}/{__version__}',
                'apiKey': self.__apikey,
                "authorization": f'Bearer {self._auth_session.access_token}'
            },
        )

    def destroy(self) -> None:
        """
        close postgrest client conn
        """
        call_as_sync(self._client.aclose)

    def set_schema(self, schema: str) -> None:
        """设置操作的表组（schema）"""
        self._client.schema(schema)

    def __get_base_query_from_path(self, path: DALPath | None = None):
        """从路径中获取查询对象"""
        dp = self.dump_path(path)
        return self._client.schema(dp[1]).from_table(dp[0])
    

    QueryTV = typing.TypeVar('QueryTV', 
        postgrest.AsyncQueryRequestBuilder,
        postgrest.AsyncFilterRequestBuilder,
        postgrest.AsyncSelectRequestBuilder
    )
    def __apply_filters_to_base_query(self, 
        base_query: QueryTV, 
        filters: typing.Iterable[DALFilter]
    ) -> QueryTV:
        """将过滤器应用到查询对象"""
        for f in filters:
            f_tuple = f.dump_to_tuple()
            f_func = getattr(base_query, f_tuple[0])
            if f_tuple[1] is not None:
                if isinstance(f_tuple[1], typing.Iterable):
                    base_query = f_func(*f_tuple[1])
                elif isinstance(f_tuple[1], dict):
                    base_query = f_func(**f_tuple[1])
            else:
                base_query = f_func()
        return base_query

    async def __execute_query(self, query: QueryTV):
        """执行编辑好的请求

        处理这些异常：
        - PGRST301 -> Unauthorized
        """
        try:
            return await query.execute()
        except postgrest.APIError as e:
            if e.code == 'PGRST301':  # JWT expired
                raise Unauthorized("token expired", self._session.token)
            
            raise e

    @typing.overload
    async def insert(self,
        to_insert: dict,
        path: typing.Optional[DALPath] = None,
        exclude_key: bool = True,
    ) -> dict:
        ...
    @typing.overload
    async def insert(self,
        to_insert: SchemeTV,
        path: typing.Optional[DALPath] = None,
        exclude_key: bool = True,
    ) -> SchemeTV:
        ...
    async def insert(
        self,
        to_insert: dict | SchemeTV,
        path = None,
        exclude_natural_key: bool = True,
    ) -> dict | SchemeTV:
        if isinstance(to_insert, BaseScheme) and path is None:
            path = to_insert.dal_path()
        
        processed_to_insert: dict
        if isinstance(to_insert, BaseScheme):
            processed_to_insert = to_insert.dump_to_dict(
                exclude_natural_key=exclude_natural_key
            )
        else:
            processed_to_insert = to_insert
        
        base_query = self.__get_base_query_from_path(path)
        query = base_query.insert(
            json=processed_to_insert
        )
        res = await self.__execute_query(query)
        
        if isinstance(to_insert, BaseScheme):
            sc = SchemeConverter(scheme_cls=to_insert.__class__)
            return sc(
                res.data[0],
                **to_insert.dump_to_dict(only_private=True)
            )
        elif isinstance(to_insert, dict):
            return res.data[0]
        
        assert False

    FieldValueTV = typing.TypeVar('FieldValueTV')

    @typing.overload
    async def select(
        self,
        to_select: typing.Type[SchemeTV],
        *filters: FilterLikeType,
        path: typing.Optional[DALPath] = None,
        task_context: Opt[ExtendedTaskContext] = None,
    ) -> typing.Tuple[SchemeTV, ...]:
        ...
    @typing.overload
    async def select(
        self,
        to_select: "Field[FieldValueTV]",
        *filters: FilterLikeType,
        path: typing.Optional[DALPath] = None,
        task_context: Opt[ExtendedTaskContext] = None,
    ) -> typing.Tuple[FieldValueTV, ...]:
        ...
    @typing.overload
    async def select(
        self,
        to_select: typing.Iterable[FieldLikeType] | None,
        *filters: FilterLikeType,
        path: typing.Optional[DALPath] = None,
        task_context: Opt[ExtendedTaskContext] = None,
    ) -> typing.Tuple[dict, ...]:
        ...
    async def select(
        self,
        to_select: typing.Union[
            typing.Type[SchemeTV], 
            "Field[FieldValueTV]",
            typing.Iterable[FieldLikeType],
            None
        ],
        *filters: FilterLikeType,
        path: typing.Optional[DALPath] = None,
        task_context: Opt[ExtendedTaskContext] = None,
    ) -> typing.Union[
        typing.Tuple[SchemeTV, ...],
        typing.Tuple[FieldValueTV, ...],
        typing.Tuple[dict, ...]
    ]:
        
        # process to_select to fields
        if to_select is None:
            fields = ("*",)
        elif isinstance(to_select, Field):
            fields = (to_select.name,)
        elif isinstance(to_select, typing.Iterable):
            fields = tuple(
                dump_field_like(i) for i in to_select
            )
        elif issubclass(to_select, BaseScheme):
            fields = ("*",)
        else:
            raise ValueError(f"Invalid type for to_select, {type(to_select)}")
        
        # process filters
        processed_filters: typing.Iterable[DALFilter] = dump_filters_like(
            *filters, scheme_like=to_select
        )

        # preprocess path
        if path is None:
            if isinstance(to_select, type) and safe_issubclass(to_select, BaseScheme): 
                path = to_select.dal_path()
            elif isinstance(to_select, Field):
                path = to_select.scheme_cls.dal_path()

        # construct query
        base_query = self.__get_base_query_from_path(path)
        base_query = base_query.select(*fields)
        query = self.__apply_filters_to_base_query(base_query, processed_filters)
        res = await self.__execute_query(query)

        if len(res.data) == 0:
            raise NotFound(path, self, filters=processed_filters)
        
        # parse res to the same as to_selec
        if isinstance(to_select, Field):
            return tuple(
                i[to_select.name] for i in res.data
            )
        elif safe_issubclass(to_select, BaseScheme): 
            sc = SchemeConverter(scheme_cls=to_select)
            return tuple(
                sc(
                    instance_dict, 
                    _task_context=task_context
                )
                for instance_dict in res.data
            )  # type: ignore
        else:
            return tuple(*res.data)
    
    async def delete(self, 
        to_delete: SchemeTV | typing.Type[SchemeTV],
        *filters: FilterLikeType,
        path: Opt[DALPath] = None,
    ) -> None:
        
        if path is None:
            if isinstance(to_delete, BaseScheme) or issubclass(to_delete, BaseScheme):
                path = to_delete.dal_path()
        
        if not filters:
            if isinstance(to_delete, BaseScheme):
                filters += (to_delete.key_eqf,)
        
        base_query = self.__get_base_query_from_path(path)
        base_query = base_query.delete()
        query = self.__apply_filters_to_base_query(
            base_query, dump_filters_like(*filters, scheme_like=to_delete)
        )
        await self.__execute_query(query)

    @typing.overload
    async def update(
        self,
        to_update: SchemeTV,
        *filters: DALFilter,
        path: Opt[DALPath] = None,
        only_dirty: bool = True,
        exclude_key: bool = True,
    ) -> SchemeTV:
        ...
    @typing.overload
    async def update(
        self,
        to_update: dict,
        *filters: DALFilter,
        path: Opt[DALPath] = None,
        only_dirty: bool = True,
        exclude_key: bool = True,
    ) -> dict:
        ...
    @typing.overload
    async def update(
        self,
        to_update: "FieldValueProxy[FieldValueTV]" | FieldValueTV,
        *filters: DALFilter,
        path: Opt[DALPath] = None,
        only_dirty: bool = True,
        exclude_key: bool = True,
    ) -> FieldValueTV:
        ...
    @typing.overload
    async def update(self,
        to_update: typing.Tuple[Field[FieldValueTV], FieldValueTV],
        *filters: DALFilter,
        path: Opt[DALPath] = None,
        only_dirty: bool = True,
        exclude_key: bool = True,
    ) -> FieldValueTV:
        ...
    async def update(
        self,
        to_update: typing.Union[
            dict, SchemeTV,
            "FieldValueProxy[FieldValueTV]",
            FieldValueTV,
            typing.Tuple[Field[FieldValueTV], FieldValueTV]
        ],
        *filters: DALFilter,
        path: Opt[DALPath] = None,
        only_dirty: bool = True,
        exclude_natural_key: bool = True,
    ) -> typing.Union[
        dict,
        SchemeTV,
        FieldValueTV,
    ]:
        # preprocess path
        if path is None: 
            if isinstance(to_update, BaseScheme):
                path = to_update.dal_path()
            elif isinstance(to_update, FieldValueProxy):
                path = to_update.scheme.dal_path()

        # preprocess filters
        if not filters:
            if isinstance(to_update, BaseScheme):
                filters += (
                    to_update.key_eqf,
                )
            elif isinstance(to_update, FieldValueProxy):
                filters += (
                    to_update.scheme.key_eqf,
                )
        
        # process to_update
        processed_to_update: typing.Dict[str, typing.Any]
        if isinstance(to_update, BaseScheme):
            processed_to_update = to_update.dump_to_dict(
                only_dirty=only_dirty,
                exclude_natural_key=exclude_natural_key
            )
        elif isinstance(to_update, FieldValueProxy):
            processed_to_update = { to_update.field.name: to_update.obj }
        elif isinstance(to_update, tuple):
            if len(to_update) != 2:
                raise ValueError(f"Invalid tuple length for to_update, {len(to_update)}")
            processed_to_update = { to_update[0].name: to_update[1] }
        elif isinstance(to_update, dict):
            processed_to_update = to_update
        else:
            raise ValueError(f"Invalid type for to_update, {type(to_update)}")

        base_query = self.__get_base_query_from_path(path)
        base_query = base_query.update(json=processed_to_update)
        query = self.__apply_filters_to_base_query(base_query, filters)
        res = await self.__execute_query(query)

        if len(res.data) == 0:
            raise UpdateFailure(path, self)  # TODO add UpdateFailure
        
        # parse res to the same as to_update
        if isinstance(to_update, BaseScheme):
            sc = SchemeConverter(scheme_cls=to_update.__class__)
            return sc(
                value=res.data[0],
                **to_update.dump_to_dict(only_private=True)
            )
        elif isinstance(to_update, FieldValueProxy):
            return res.data[0][to_update.field.name]
        elif isinstance(to_update, tuple):
            return res.data[0][to_update[0].name]
        elif isinstance(to_update, dict):
            return res.data[0]
        
        assert False

    async def upsert(self):  # TODO
        return await super().upsert()
