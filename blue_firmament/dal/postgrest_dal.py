
import postgrest
import typing
import asyncio
import enum
from typing import Optional as Opt

from ..utils.type import safe_issubclass
from .exceptions import NotFound, UpdateFailure
from ..scheme.field import BlueFirmamentField, FieldValueProxy, FieldValueType
from ..dal.filters import *
from .base import DataAccessObject
from .. import __version__, __name__ as __package_name__
from . import (
    DALPath, FieldLikeType, FilterLikeType, dump_field_like, dump_filters_like
)
from .filters import DALFilter
from ..utils import dump_enum
from . import StrictDALPath
from ..data.settings.dal import get_setting as get_dal_setting
from ..transport import HeaderName
from ..scheme import BaseScheme


class PostgrestDataAccessObject(DataAccessObject):

    '''基于PostgREST的DAO实现
    
    TODO
    -----
    - 如果token无效，应当自动删除
    '''

    SERV_DAO: typing.Self = None  # type: ignore[assignment]
    '''PostgrestDAO的服务角色数据访问对象（全局实例）'''
    ANON_DAO: typing.Self = None  # type: ignore[assignment]
    '''PostgrestDAO的匿名角色数据访问对象（全局实例）'''

    def __init__(self,
        url: typing.Optional[str] = None,
        default_table: typing.Optional[str | enum.Enum] = None,
        default_schema: typing.Optional[str | enum.Enum] = None,
        token: typing.Optional[str] = None,
        supabase_api_key: typing.Optional[str] = None,
    ) -> None:
        
        '''实例化

        :param url: PostgREST的URL地址
        :param schema: 操作的表组
        :param token: PostgREST的认证令牌 会被附加到 ``Authorization`` 请求头中，添加 ``Bearer `` 前缀
        :param supabase_api_key: Supabase的API密钥 会被附加到 ``apiKey`` 请求头中；不提供默认使用anon_key
        '''
        base_url = url or get_dal_setting().postgrest_url
        default_schema = default_schema or get_dal_setting().postgrest_default_schema
        default_table = default_table or get_dal_setting().postgres_default_table
        supabase_api_key = supabase_api_key or get_dal_setting().postgrest_anonymous_token

        self.__headers = {
            'X-Client-Info': f'{__package_name__}/{__version__}',
            'apiKey': supabase_api_key,
        }
        '''PostgREST客户端使用的请求头'''

        if token:
            self.__headers[HeaderName.AUTHORIZATION.value] = f'Bearer {token}'
        
        self.__client = postgrest.AsyncPostgrestClient(
            base_url=base_url,
            schema=dump_enum(default_schema),
            headers=self.__headers,
        )

        super().__init__(StrictDALPath(
            (dump_enum(default_table), dump_enum(default_schema),)
        ))

    def destory(self) -> None:
        '''销毁DAO实例
        
        - 关闭PostgREST客户端连接
        '''
        asyncio.get_event_loop().run_until_complete(
            self.__client.aclose()
        )

    def set_token(self, token: str) -> None:

        '''设置认证令牌

        NEED TEST
        '''
        self.__headers[HeaderName.AUTHORIZATION.value] = f'Bearer {token}'

    def unset_token(self) -> None:
            
        '''取消认证令牌

        NEED TEST
        '''
        if HeaderName.AUTHORIZATION.value in self.__headers:
            del self.__headers[HeaderName.AUTHORIZATION.value]

    def set_schema(self, schema: str) -> None:

        '''设置操作的表组（schema）
        '''
        self.__client.schema(schema)

    def __get_base_query_from_path(self, path: DALPath | None = None):

        '''从路径中获取查询对象
        '''
        dp = self.dump_path(path)
        return self.__client.schema(dp[1]).from_table(dp[0])
    

    BASE_QUERY_TYPEVAR = typing.TypeVar('BASE_QUERY_TYPEVAR', 
        postgrest.AsyncQueryRequestBuilder,
        postgrest.AsyncFilterRequestBuilder,
        postgrest.AsyncSelectRequestBuilder
    )
    def __apply_filters_to_base_query(self, 
        base_query: BASE_QUERY_TYPEVAR, 
        filters: typing.Iterable[DALFilter]
    ) -> BASE_QUERY_TYPEVAR:

        '''将过滤器应用到查询对象
        '''
        for f in filters:
            f_tuple = f.dump_to_tuple()
            f_func = getattr(base_query, f_tuple[0])
            if f_tuple[1] is not None:
                base_query = f_func(*f_tuple[1])
            else:
                base_query = f_func()
        return base_query

    BaseSchemeType = typing.TypeVar('BaseSchemeType', bound="BaseScheme")

    @typing.overload
    async def insert(self,
        to_insert: dict,
        path: typing.Optional[DALPath] = None,
        exclude_primary_key: bool = True,
    ) -> dict:
        pass

    @typing.overload
    async def insert(self,
        to_insert: BaseSchemeType,
        path: typing.Optional[DALPath] = None,
        exclude_primary_key: bool = True,
    ) -> BaseSchemeType:
        pass

    async def insert(self, 
        to_insert: dict | BaseSchemeType, 
        path = None,
        exclude_primary_key: bool = True,
    ) -> dict | BaseSchemeType: 
        
        if isinstance(to_insert, BaseScheme):
            to_insert = to_insert.dump_to_dict(exclude_primary_key=exclude_primary_key)
        
        if isinstance(to_insert, BaseScheme) and path is None:
            path = DALPath((to_insert.__table_name__, to_insert.__schema_name__))
        base_query = self.__get_base_query_from_path(path)
        res = await base_query.insert(
            json=to_insert
        ).execute()
        
        if isinstance(to_insert, BaseScheme):
            scheme_ins: BaseScheme = to_insert.__class__(**res.data[0])
            return scheme_ins
        elif isinstance(to_insert, dict):
            return res.data[0]
        
        assert False

    FieldValueType = typing.TypeVar('FieldValueType')

    @typing.overload
    async def select(self,
        to_select: typing.Type[BaseSchemeType],
        *filters: FilterLikeType,
        path: typing.Optional[DALPath] = None,
    ) -> typing.Tuple[BaseSchemeType, ...]:
        ...

    @typing.overload
    async def select(self,
        to_select: "BlueFirmamentField[FieldValueType]",
        *filters: FilterLikeType,
        path: typing.Optional[DALPath] = None,
    ) -> typing.Tuple[FieldValueType, ...]:
        ...

    @typing.overload
    async def select(self,
        to_select: typing.Iterable[FieldLikeType] | None,
        *filters: FilterLikeType,
        path: typing.Optional[DALPath] = None,
    ) -> typing.Tuple[dict, ...]:
        ...

    async def select(self,
        to_select: typing.Union[
            typing.Type[BaseSchemeType], 
            "BlueFirmamentField[FieldValueType]",
            typing.Iterable[FieldLikeType],
            None
        ],
        *filters: FilterLikeType,
        path: typing.Optional[DALPath] = None,
    ) -> typing.Union[
            typing.Tuple[BaseSchemeType, ...],
            typing.Tuple[FieldValueType, ...],
            typing.Tuple[dict, ...]
        ]:
        
        # process to_select to fields
        if to_select is None:
            fields = ("*",)
        elif isinstance(to_select, BlueFirmamentField):
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
            *filters, scheme=to_select
        )

        # preprocess path
        if path is None:
            if isinstance(to_select, type) and safe_issubclass(to_select, BaseScheme): 
                path = to_select.dal_path()
            elif isinstance(to_select, BlueFirmamentField):
                path = to_select.scheme_cls.dal_path()

        # construct query
        base_query = self.__get_base_query_from_path(path)
        base_query = base_query.select(*fields)
        base_query = self.__apply_filters_to_base_query(base_query, processed_filters)
        res = await base_query.execute()

        if len(res.data) == 0:
            raise NotFound(path, self, filters=processed_filters)
        
        # parse res to the same as to_selec
        if isinstance(to_select, BlueFirmamentField):
            return tuple(
                i[to_select.name] for i in res.data
            )
        elif isinstance(to_select, type) and safe_issubclass(to_select, BaseScheme): 
            return tuple(
                to_select(**instance_dict) for instance_dict in res.data
            )
        else:
            return tuple(res.data)
    
    async def delete(self, 
        to_delete: BaseSchemeType | typing.Type[BaseSchemeType],
        *filters: FilterLikeType,
        path: Opt[DALPath] = None,
    ) -> None:
        
        if path is None:
            if isinstance(to_delete, BaseScheme) or issubclass(to_delete, BaseScheme):
                path = to_delete.dal_path()
        
        if not filters:
            if isinstance(to_delete, BaseScheme):
                filters += (to_delete.primary_key_eqf,)
        
        base_query = self.__get_base_query_from_path(path)
        base_query = base_query.delete()
        base_query = self.__apply_filters_to_base_query(
            base_query, dump_filters_like(*filters, scheme=to_delete)
        )
        await base_query.execute()

    DictType = typing.TypeVar('DictType', bound=dict)

    @typing.overload
    async def update(self,
        to_update: BaseSchemeType,
        *filters: DALFilter,
        path: Opt[DALPath] = None,
        only_dirty: bool = True,
    ) -> BaseSchemeType:
        ...

    @typing.overload
    async def update(self,
        to_update: DictType,
        *filters: DALFilter,
        path: Opt[DALPath] = None,
        only_dirty: bool = True,
    ) -> DictType:
        ...

    @typing.overload
    async def update(self,
        to_update: "FieldValueProxy[FieldValueType]" | FieldValueType,
        *filters: DALFilter,
        path: Opt[DALPath] = None,
        only_dirty: bool = True,
    ) -> FieldValueType:
        ...

    async def update(self,
        to_update: typing.Union[
            DictType, BaseSchemeType,
            "FieldValueProxy[FieldValueType]",
            FieldValueType
        ],
        *filters: DALFilter,
        path: Opt[DALPath] = None,
        only_dirty: bool = True,
    ) -> typing.Union[
            DictType, BaseSchemeType, FieldValueType,
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
                    to_update.primary_key_eqf,
                )
            elif isinstance(to_update, FieldValueProxy):
                filters += (
                    to_update.scheme.primary_key_eqf,
                )
        
        # process to_update
        processed_to_update: typing.Dict[str, typing.Any]
        if isinstance(to_update, BaseScheme):
            processed_to_update = to_update.dump_to_dict(only_dirty=only_dirty)
        elif isinstance(to_update, FieldValueProxy):
            processed_to_update = { to_update.field.name: to_update.obj }
        elif isinstance(to_update, dict):
            processed_to_update = to_update
        else:
            raise ValueError(f"Invalid type for to_update, {type(to_update)}")

        base_query = self.__get_base_query_from_path(path)
        base_query = base_query.update(json=processed_to_update)
        base_query = self.__apply_filters_to_base_query(base_query, filters)
        res = await base_query.execute()

        if len(res.data) == 0:
            raise UpdateFailure(path, self)
        
        # parse res to the same as to_update
        if isinstance(to_update, BaseScheme):
            return to_update.__class__(**res.data[0]) 
        elif isinstance(to_update, FieldValueProxy):
            return res.data[0][to_update.field.name]
        elif isinstance(to_update, dict):
            return res.data[0]
        
        assert False

    async def upsert(self):  # TODO
        return await super().upsert()
