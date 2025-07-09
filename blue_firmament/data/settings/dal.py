
from ...setting import Setting, make_setting_singleton


class DALSetting(Setting):

    _setting_name: str = "dal"

    postgrest_url: str = 'http://localhost:3000'
    '''默认PostgREST的URL地址'''
    postgrest_default_schema: str = 'public'
    '''默认PostgREST的默认表组（schema）'''
    postgres_default_table: str = 'default_table'
    '''默认PostgreSQL的默认表名（table）'''
    postgrest_anonymous_token: str = ''
    '''默认PostgREST的匿名访问令牌（仅在Supabase Postgrest中使用）'''
    postgrest_service_token: str = ''
    '''默认PostgREST的服务访问令牌（仅在Supabase Postgrest中使用）'''

    redis_host: str = 'localhost'
    '''默认Redis服务器的主机名'''
    redis_port: int = 6379
    '''默认Redis服务器的端口号'''
    redis_password: str = ''
    '''默认Redis服务器的密码'''
    redis_db: int = 0
    '''默认Redis服务器的数据库编号'''


get_setting, set_setting = make_setting_singleton(DALSetting())

