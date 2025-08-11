"""PostgrestDAL
"""

import postgrest

from ..task.context import ExtendedTaskContext
from .._types import _undefined
from ..scheme.converter import SchemeConverter
from .utils import dump_query_coms_like
from ..exceptions import Unauthorized
from ..utils.typing_ import safe_issubclass
from ..exceptions import NotFound
from ..scheme.field import Field, FieldValueProxy, FieldValueTV
from blue_firmament.dal.query_components.filters import *
from .base import TableLikeDataAccessLayer, DataAccessLayerWithAuth
from .. import __version__, __name__ as __package_name__
from .types import (
    DALPath, FieldLikeType, QueryComLikeType, StrictDALPath
)
from .query_components import DALQueryComponent
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
                **({"authorization": f'Bearer {self._auth_session.access_token}'}
                    if self._auth_session else {})
            }
        )

    async def close(self) -> None:
        await self._client.aclose

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
    def __apply_filters_to_base_query(
        self,
        base_query: QueryTV,
        query_coms: typing.Iterable[DALQueryComponent]
    ) -> QueryTV:
        """将过滤器应用到查询对象

        :param base_query: 基础查询对象
        :param query_coms: 过滤器列表
        """
        for query_com in query_coms:
            dumped_query_com = query_com.dump_to_postgrest()
            req_builer_method = getattr(base_query, dumped_query_com[0])
            if isinstance(dumped_query_com[1], tuple):
                base_query = req_builer_method(*dumped_query_com[1])
            elif isinstance(dumped_query_com[1], dict):
                base_query = req_builer_method(**dumped_query_com[1])
            else:
                base_query = req_builer_method()
        return base_query

    async def __execute_query(self, query: QueryTV):
        """执行编辑好的请求

        处理这些异常：
        - PGRST301 -> Unauthorized
        - code42501 -> New row violates row-level security policy
        """
        try:
            return await query.execute()
        except postgrest.APIError as e:
            if e.code == 'PGRST301':  # JWT expired
                raise Unauthorized("token expired", self._auth_session.access_token)
            
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
        *filters: QueryComLikeType,
        path: typing.Optional[DALPath] = None,
        task_context: Opt[ExtendedTaskContext] = None,
    ) -> typing.Tuple[SchemeTV, ...]:
        ...
    @typing.overload
    async def select(
        self,
        to_select: "Field[FieldValueTV]",
        *filters: QueryComLikeType,
        path: typing.Optional[DALPath] = None,
        task_context: Opt[ExtendedTaskContext] = None,
    ) -> typing.Tuple[FieldValueTV, ...]:
        ...
    @typing.overload
    async def select(
        self,
        to_select: typing.Iterable[FieldLikeType] | None,
        *filters: QueryComLikeType,
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
        *query_coms: QueryComLikeType,
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

        # preprocess path
        if path is None:
            if isinstance(to_select, type) and safe_issubclass(to_select, BaseScheme):
                path = to_select.dal_path()
            elif isinstance(to_select, Field):
                path = to_select.scheme_cls.dal_path()

        # process query components
        prcesd_query_coms: typing.Iterable[DALQueryComponent] = dump_query_coms_like(
            *query_coms, scheme_like=to_select
        )
        ref_fields = set()
        for i, query_com in enumerate(prcesd_query_coms):
            if isinstance(query_com, DALFilter):
                filter_dal_path = query_com.dal_path
                if (
                    filter_dal_path is not None and
                    filter_dal_path[0] != path[0]
                ):
                    ref_fields.add(f"{filter_dal_path[0]}({query_com.field_name})")
                    prcesd_query_coms[i] = query_com.fork(use_fqfn=True)

        # construct query
        base_query = self.__get_base_query_from_path(path)
        base_query = base_query.select(*fields, *ref_fields)
        query = self.__apply_filters_to_base_query(base_query, prcesd_query_coms)
        res = await self.__execute_query(query)

        if len(res.data) == 0:
            raise NotFound(str(path))  # TODO self, filters=processed_filters
        
        # parse res to the same as to_selec
        if isinstance(to_select, Field):
            return tuple(
                to_select.load_val(i[to_select.name])
                for i in res.data
            )
        elif safe_issubclass(to_select, BaseScheme): 
            sc = SchemeConverter(scheme_cls=to_select)
            return tuple(
                sc(
                    instance_dict, 
                    _task_context=task_context or _undefined
                )
                for instance_dict in res.data
            )  # type: ignore
        else:
            return tuple(*res.data)
    
    async def delete(
        self,
        to_delete: SchemeTV | typing.Type[SchemeTV],
        *query_coms: QueryComLikeType,
        path: Opt[DALPath] = None,
     ) -> None:
        
        if path is None:
            if isinstance(to_delete, BaseScheme) or issubclass(to_delete, BaseScheme):
                path = to_delete.dal_path()
        
        if not query_coms:
            if isinstance(to_delete, BaseScheme):
                query_coms += (to_delete.key_eqf,)
        
        base_query = self.__get_base_query_from_path(path)
        base_query = base_query.delete()
        query = self.__apply_filters_to_base_query(
            base_query, dump_query_coms_like(*query_coms, scheme_like=to_delete)
        )
        res = await self.__execute_query(query)

        if len(res.data) == 0:
            raise DeleteFailure(path, self)  # TODO add NoEffect (checkout filters, RLS)

    @typing.overload
    async def update(
        self,
        to_update: SchemeTV,
        *filters: DALQueryComponent,
        path: Opt[DALPath] = None,
        only_dirty: bool = True,
        exclude_natural_key: bool = True,
    ) -> SchemeTV:
        ...
    @typing.overload
    async def update(
        self,
        to_update: dict,
        *filters: DALQueryComponent,
        path: Opt[DALPath] = None,
        only_dirty: bool = True,
        exclude_natural_key: bool = True,
    ) -> dict:
        ...
    @typing.overload
    async def update(
        self,
        to_update: "FieldValueProxy[FieldValueTV]" | FieldValueTV,
        *filters: DALQueryComponent,
        path: Opt[DALPath] = None,
        only_dirty: bool = True,
        exclude_natural_key: bool = True,
    ) -> FieldValueTV:
        ...
    @typing.overload
    async def update(
        self,
        to_update: typing.Tuple[Field[FieldValueTV], FieldValueTV],
        *filters: DALQueryComponent,
        path: Opt[DALPath] = None,
        only_dirty: bool = True,
        exclude_natural_key: bool = True,
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
        *query_coms: DALQueryComponent,
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
        if not query_coms:
            if isinstance(to_update, BaseScheme):
                query_coms += (
                    to_update.key_eqf,
                )
            elif isinstance(to_update, FieldValueProxy):
                query_coms += (
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
            processed_to_update = {to_update.field.name: to_update.obj}
        elif isinstance(to_update, tuple):
            if len(to_update) != 2:
                raise ValueError(f"Invalid tuple length for to_update, {len(to_update)}")
            processed_to_update = { to_update[0].name: to_update[1] }
        elif isinstance(to_update, dict):
            processed_to_update = {
                k.name if isinstance(k, Field) else k: v
                for k, v in to_update.items()
            }
        else:
            raise ValueError(f"Invalid type for to_update, {type(to_update)}")

        base_query = self.__get_base_query_from_path(path)
        base_query = base_query.update(json=processed_to_update)
        query = self.__apply_filters_to_base_query(base_query, query_coms)
        res = await self.__execute_query(query)

        if len(res.data) == 0:
            raise UpdateFailure(path, self)  # TODO add NoEffect (checkout filters, RLS)
        
        # parse res to the same as to_update
        if isinstance(to_update, BaseScheme):
            sc = SchemeConverter(scheme_cls=to_update.__class__)
            return sc(
                value=res.data[0],
                **to_update.dump_to_dict(only_private=True)
            )
        elif isinstance(to_update, FieldValueProxy):
            return to_update.field.load_val(res.data[0][to_update.field.name])
        elif isinstance(to_update, tuple):
            return res.data[0][to_update[0].name]
        elif isinstance(to_update, dict):
            return res.data[0]
        
        assert False

    async def upsert(self):  # TODO
        return await super().upsert()
