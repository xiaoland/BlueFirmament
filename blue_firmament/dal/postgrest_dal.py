
import postgrest
import typing
import asyncio
import enum

from blue_firmament.dal import DALPath
from blue_firmament.dal.filters import DALFilter
from .. import __version__, __name__ as __package_name__
from ..utils import dump_enum
from . import DataAccessObject, StrictDALPath
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

    async def insert(self, to_insert, path = None):  # type: ignore[override]
        
        processed_to_insert = []
        if isinstance(to_insert, list):
            for item in to_insert:
                if isinstance(item, dict):
                    processed_to_insert.append(item)
                elif isinstance(item, BaseScheme):
                    processed_to_insert.append(item.dump_to_dict())
                else:
                    raise TypeError(f'Invalid type of to_insert item: {type(item)}')
        elif isinstance(to_insert, dict) or isinstance(to_insert, BaseScheme):
            processed_to_insert.append(to_insert)
        else:
            raise TypeError(f'Invalid type of to_insert: {type(to_insert)}')
        
        if isinstance(to_insert, BaseScheme) and path is None:
            path = DALPath((to_insert.__table_name__, to_insert.__schema_name__))
        base_query = self.__get_base_query_from_path(path)
        res = await base_query.insert(
            json=processed_to_insert
        ).execute()
        
        if isinstance(to_insert, list):
            res_data: typing.List[dict | BaseScheme] = []
            for i in to_insert:
                if isinstance(i, BaseScheme):
                    primary_key = i.get_primary_key()
                    for res_item in res.data:
                        # BUG 如果 primary_key 字段在数据模型中的名称和字段.name不一致，会导致错误（AttributeNotFound）
                        if res_item[primary_key] == getattr(i, primary_key):
                            res_data.append(i.__class__(**res_item))
                            break

                    # 不可能出现找不到的情况，因为事务是原子性的
                elif isinstance(i, dict):
                    res_data.append(i)

            return res_data
        elif isinstance(to_insert, BaseScheme):
            scheme_ins: BaseScheme = to_insert.__class__(**res.data[0])
            return scheme_ins
        elif isinstance(to_insert, dict):
            return res.data[0]
        
        assert False

    async def select(self, 
        *filters: DALFilter, 
        path: DALPath | None = None, 
        fields: typing.Iterable[str | enum.Enum] | None = None
    ) -> typing.Tuple[dict, ...]:
        
        if fields is None:
            fields = ("*",)
        else:
            fields = tuple(dump_enum(i) for i in fields)

        # construct query
        base_query = self.__get_base_query_from_path(path)
        base_query = base_query.select(
            *fields
        )
        base_query = self.__apply_filters_to_base_query(base_query, filters)

        res = await base_query.execute()
        if isinstance(res.data, dict):
            res_data = (res.data,)
        else:
            res_data = tuple(res.data)
        return res_data
    
    async def delete(self, *filters: DALFilter, path: DALPath | None = None) -> None:
        
        base_query = self.__get_base_query_from_path(path)
        base_query = base_query.delete()
        base_query = self.__apply_filters_to_base_query(base_query, filters)
        res = await base_query.execute()

    async def update(self, # type: ignore[override]
        to_update: dict | BaseScheme, path: DALPath | None = None, /, *filters: DALFilter
    ) -> dict | BaseScheme:
        
        if not path and isinstance(to_update, BaseScheme):
            path = DALPath((to_update.__table_name__, to_update.__schema_name__))

        if not filters:
            raise ValueError("At least one filter is required for update.")

        base_query = self.__get_base_query_from_path(path)
        base_query = base_query.update(
            json=to_update.dump_to_dict() if isinstance(to_update, BaseScheme) else to_update
        )
        base_query = self.__apply_filters_to_base_query(base_query, filters)
        res = await base_query.execute()

        # TODO 因为RLS导致的失败也应该有Exception
        
        # parse res to the same as to_update
        if isinstance(to_update, BaseScheme):
            return to_update.__class__(**res.data[0])  # TODO if partial scheme, use full scheme to parse
        elif isinstance(to_update, dict):
            return res.data[0]
        
        assert False

    async def upsert(self):  # TODO
        return await super().upsert()
