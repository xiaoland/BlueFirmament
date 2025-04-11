
from ...setting import Setting, make_setting_singleton


class DALSetting(Setting):
    '''数据访问层相关配置'''

    _setting_name: str = "dal"

    postgrest_url: str = 'http://localhost:3000'
    '''PostgREST的URL地址'''
    postgrest_default_schema: str = 'public'
    '''PostgREST的默认表组（schema）'''
    postgres_default_table: str = 'default_table'
    '''PostgreSQL的默认表名（table）'''
    postgrest_anonymous_token: str = ''
    '''PostgREST的匿名访问令牌（仅在Supabase Postgrest中使用）'''


get_setting, set_setting = make_setting_singleton(DALSetting())

