'''CommonManager Module

References
----------
- `issue#5 <https://github.com/xiaoland/BlueFirmament/issues/5>`_
'''

import typing
from typing import Literal as L, Optional as Opt

from blue_firmament.scheme.field import FieldValueProxy
from blue_firmament.utils import get_optional

from ..log import get_logger
from .main import BaseManager, SchemeType
from ..session.common import CommonSession
from ..utils.type import add_type_to_namespace, safe_issubclass
from ..transport import TransportOperationType
from ..scheme import BaseScheme

if typing.TYPE_CHECKING:
    from ..main import BlueFirmamentApp
    from ..scheme.field import BlueFirmamentField
    from ..dal.base import DataAccessObject


logger = get_logger(__name__)


T = typing.TypeVar('T')
PrimaryKeyType = typing.TypeVar('PrimaryKeyType', str, int)
'''管理器管理的数据模型的主键类型
'''
class CommonManager(
    typing.Generic[SchemeType, PrimaryKeyType],
    BaseManager[SchemeType, CommonSession]
):
    
    """通用管理器类

    在管理器基类的基础上封装了一系列有用的方法，帮助更快地编写管理器
    
    Features
    --------
    - `property dao`: 获取当前管理器所属会话的 DAO 实例
    - `override get_scheme`: 覆盖了获取数据模型的方法，变为通过 `_get` 获取

    数据操作类
    ^^^^^^^^^^^
    都支持 `dao` 参数，用于指定 session.dao 以外的 DAO 实例，在需要特殊权限时很有用

    - `method _get`: 获取数据模型实例，主键
    - `method _insert`: 插入数据模型实例

    Terms
    -----
    - 当前实例: 通过 :meth:`BaseManager.get_scheme_safe` 获取的数据模型实例

    TODO
    ----
    - 允许用户设置主键值的 fallback （比如为会话的用户 ID）
    
    """
    
    @property
    def dao(self) -> "DataAccessObject":
        """获取当前管理器所属会话的 DAO 实例"""
        return self.session.dao
    
    def dump_dao(self, dao: Opt["DataAccessObject"] = None) -> "DataAccessObject":

        """
        解析可选型的 ``dao`` 参数

        如果提供了 ``dao`` 则返回它，否则返回当前会话的 DAO 实例
        """
        return get_optional(dao, self.dao)

    FieldType = typing.TypeVar('FieldType', bound="BlueFirmamentField")
    
    async def get_scheme(self,
        _id: Opt[PrimaryKeyType] = None,
        dao: Opt["DataAccessObject"] = None
    ) -> SchemeType:
        
        try:
            return await super().get_scheme()
        except ValueError as e:
            if _id is not None:
                return await self._get(_id=_id, dao=dao)
            raise e
    
    async def _get(self, 
        _id: PrimaryKeyType, 
        dao: Opt["DataAccessObject"] = None
    ) -> SchemeType:
        
        """获取数据模型实例

        获取成功则设置为当前实例

        :param _id: 数据模型实例的主键值
        :param dao: 数据访问对象；不提供则使用当前会话的 DAO
        """
        res = await self.dump_dao(dao).select_one(self.scheme_cls, _id)
        self.set_scheme(res)
        return res
    
    async def _insert(self, 
        scheme: Opt[SchemeType],
        dao: Opt["DataAccessObject"] = None
    ) -> SchemeType:
        
        """插入数据模型实例到 DAO

        插入成功则设置为当前实例
        
        :param scheme: 数据模型实例；不提供则为当前实例
        """
        if not scheme:
            scheme = await self.get_scheme()
        
        res = await self.dump_dao(dao).insert(to_insert=scheme)
        self.set_scheme(res)
        return res

    async def _get_a_field(self, 
        field: "BlueFirmamentField[T]", _id: Opt[PrimaryKeyType] = None,
        dao: Opt["DataAccessObject"] = None
    ) -> T:
        
        """获取一个字段的值

        :param _id: 主键值；没有则从当前实例获取

        :returns: 字段的值（未代理）
        """

        if not _id:
            scheme = self.get_scheme_safe()
        else:
            scheme = None
        
        if not scheme:
            return await self.dump_dao(dao).select_one(
                field, self.scheme_cls.get_primary_key().equals(_id)
            )
        else:
            return FieldValueProxy.dump(scheme.get_value(field))
    
    async def _insert_item(self, 
        field: "BlueFirmamentField[typing.List[T]]", values: typing.Iterable[T],
        _id: Opt[PrimaryKeyType] = None,
        mode: L['append', 'prepend', 'insert'] = 'append',
        at: Opt[int] = None,
        dao: Opt["DataAccessObject"] = None
    ) -> typing.List[T]:
        
        """插入条目到列表型字段值

        :param _id: 主键值；没有则从当前实例获取
        :param field: 要插入到的字段；值必须是列表类型
        :param values: 要插入的值（可多个）；
        :param mode: 插入模式 

            - append: `[raw][values]`
            - prepend: `[values][raw]`
            - insert: `[raw before at][values][raw after at]`
        :param at: 插入位置；仅当 mode 为 `insert`
        """
        field_value = await self._get_a_field(_id=_id, field=field, dao=dao)

        if isinstance(field_value, list):
            if mode == 'append':
                field_value.extend(values)
            elif mode == 'prepend':
                field_value[:0] = values
            elif mode == 'insert':
                if at is None:
                    raise ValueError('at must be provided when mode is insert')
                field_value[at:at] = values
            else:
                raise ValueError(f'Invalid mode {mode} for insert item')

            return await self._put_a_field(
                field=field, value=field_value, _id=_id, dao=dao
            )
        else:
            raise ValueError(f'DAO not returning valid value of field {field}, {field_value}')
    
    async def _put_a_field(self, 
        field: "BlueFirmamentField[T]", 
        value: T,  
        _id: Opt[PrimaryKeyType] = None,
        dao: Opt["DataAccessObject"] = None
    ) -> T:
        
        """更新字段

        :param _id: 主键值；没有则从当前实例获取
        """        
        if not _id:
            return (await self.dump_dao(dao).update(
                {field.name: value}, 
                (await self.get_scheme()).primary_key_eqf,
                path=self.scheme_cls.dal_path()
            ))[field.name]
            
        else:
            return (await self.dump_dao(dao).update(
                {field.name: value},
                self.scheme_cls.get_primary_key().equals(_id),
                path=self.scheme_cls.dal_path()
            ))[field.name]
    
    async def _delete_item(self, 
        field: "BlueFirmamentField[typing.List[T]]", 
        values: typing.Union[
            typing.Iterable[T],
            typing.Set[T]
        ],
        _id: Opt[PrimaryKeyType] = None,
        dao: Opt["DataAccessObject"] = None,
    ) -> typing.List[T]:
        
        """从列表型字段值中删除条目

        :param _id: 主键值；没有则从当前实例获取
        :param field: 要删除的字段；值必须是列表类型
        :param values: 要删除的值（可多个）；
        :param dao: 数据访问对象；不提供则使用当前会话的 DAO

        Implementation
        --------------
        高效删除
        ^^^^^^^^
        因为要删除的数量不可能大于当前列表的长度
        """
        field_value = await self._get_a_field(_id=_id, field=field, dao=dao)

        if isinstance(values, typing.Sequence):
            field_value = [v for v in field_value if v not in values]
        elif isinstance(values, (typing.Iterable)):
            for value in values:
                field_value.remove(value)
        else:
            raise ValueError(f'{field} value invalid, value is {field_value}')

        return await self._put_a_field(
            _id=_id, field=field, value=field_value, dao=dao
        )


class GetAFieldOptions(typing.TypedDict):
    fields: typing.Iterable["BlueFirmamentField"]

class CreateOptions(typing.TypedDict):
    disabled_fields: typing.Iterable["BlueFirmamentField"]

class InsertItemOptions(typing.TypedDict):
    fields: typing.Iterable["BlueFirmamentField"]

class DeleteItemOptions(typing.TypedDict):
    fields: typing.Iterable["BlueFirmamentField"]

class PatchOptions(typing.TypedDict):
    available_fields: typing.Iterable["BlueFirmamentField"]

class PutAFieldOptions(typing.TypedDict):
    fields: typing.Iterable["BlueFirmamentField"]

class PutOptions(typing.TypedDict):
    disabled_fields: typing.Iterable["BlueFirmamentField"]


ManagerType = typing.TypeVar('ManagerType', bound=CommonManager)
def common_handler_adder(
    manager_name: str,
    get: bool = False,
    get_a_field: bool = False,
    get_a_field_options: Opt[GetAFieldOptions] = None,
    create: bool = False,
    create_options: Opt[CreateOptions] = None,
    insert_item: bool = False,
    insert_item_options: Opt[InsertItemOptions] = None,
    patch: bool = False,
    patch_options: Opt[PatchOptions] = None,
    put_a_field: bool = False,
    put_a_field_options: Opt[PutAFieldOptions] = None,
    put: bool = False,
    put_options: Opt[PutOptions] = None,
    delete_item: bool = False,
    delete_item_options: Opt[DeleteItemOptions] = None,
    app: Opt["BlueFirmamentApp"] = None
):

    """A decorator adding common handlers to a manager.

    :param app: if provided, register handlers to app

    TODO
    ----
    - insert and delete item limit body's type more accurately (item's type)
        - this will bring a better validation before reach the handler
    - create
        - scheme provide a method to fastly reset disabled fields to default value
    - patch
    - put

    Features
    --------
    Get
    ^^^
    - A handler return a scheme using session DAO to select record by primary key

    Get a Field
    ^^^^^^^^^^^
    - A handler return a field of the scheme using session DAO to select record by primary key
    - Route `GET /<manager_name>/{<manager_name>_id}/<field_name>`

    Create
    ^^^^^^^^^^^^^^
    - A handler insert a record into session DAO with provided scheme data.
    - Only fields not in `disabled_fields` will be inserted, others will be ignored.

    Insert item
    ^^^^^^^^^^^^^^
    - A handler insert item(s) into an insertable field of the scheme using session DAO.
    - Route `POST /<manager_name>/{<manager_name>_id>/<field_name>`
    - Request body is a list of items to insert

    Patch
    ^^^^^
    - A handler update provided fields of the scheme into session DAO.
    - Only fields in `available_fields` will be updated, other will be ignored.

    Put a Field
    ^^^^^^^^^^^
    - A handler update a field of the scheme into session DAO.
    - Every field in `fields` will get a handler.
    - Route `PUT /<manager_name>/{<manager_name>_id}/<field_name>`
    - Request body is the new value to put

    Example
    -------
    .. code-block:: python
        @common_manager_adder(
            'user',
            put_a_field=True,
            put_a_field_options={
                'fields': (UserScheme.nickname,)
            }
        )
        class UserManager(BaseManager[UserScheme, Session]):
            __SCHEME_CLS__ = UserScheme
            __name__ = 'user'

        reg = UserManager.get_route_record_register(app)
        reg(GET, '')

    Implementation
    --------------
    Add handler to manager
    ^^^^^^^^^^^^^^^^^^^^^^^
    handler func are dynamically generated from `exec`, so it can has \n
    dynamic name
    """

    def wrapper(manager_cls: typing.Type[ManagerType]):

        if app:
            register = manager_cls.get_route_record_register(app)
        else:
            register = None

        if safe_issubclass(manager_cls.__scheme_cls__, BaseScheme):
            primary_key_field = manager_cls.__scheme_cls__.get_primary_key()
        else:
            primary_key_field = None

        result_namespaces = {}

        if get:
            # TODO not tested yet
            if not primary_key_field:
                raise ValueError('primary key is required for get')
            
            exec_namespaces = globals().copy()
            add_type_to_namespace(
                primary_key_field.vtype, exec_namespaces
            )
            
            get_handler_name = f'get_{manager_name}'
            primary_key_name = f"{manager_name}_id"
            func_sig = f"async def {get_handler_name}(self, \n"
            func_sig += f"{primary_key_name}: {primary_key_field.vtype.__name__}"
            func_sig += "):\n"
            func_body = f"    return await self._get(_id={primary_key_name})\n"
            func_str = func_sig + func_body
            
            exec(func_str, exec_namespaces, result_namespaces)
            setattr(
                manager_cls, get_handler_name, 
                result_namespaces[get_handler_name]
            )

            if register:
                register(
                    TransportOperationType.GET,
                    '/{' + primary_key_name + '}',
                    getattr(manager_cls, get_handler_name),
                )

        if put_a_field:
            if not put_a_field_options:
                raise ValueError('options are required for put_a_field')
            if not primary_key_field:
                raise ValueError('primary key is required for put_a_field')
            
            exec_namespaces = globals().copy()
            add_type_to_namespace(
                primary_key_field.vtype, exec_namespaces
            )
            
            fields = put_a_field_options.get('fields')
            for field in fields:

                put_a_field_handler_name = f'put_{field.name}'
                primary_key_name = f"{manager_name}_id"
                func_sig = f"async def {put_a_field_handler_name}(self, body, \n"
                func_sig += f"{primary_key_name}: {primary_key_field.vtype.__name__}"
                func_sig += "):\n"
                func_body = f"    return await self._put_a_field(_id={primary_key_name},\n"
                func_body += f"        field=self.scheme_cls.{field.in_scheme_name},\n"
                func_body += f"        value=body\n"
                func_body += f"    ) \n"
                func_str = func_sig + func_body
                
                exec(func_str, exec_namespaces, result_namespaces)
                setattr(
                    manager_cls, put_a_field_handler_name, 
                    result_namespaces[put_a_field_handler_name]
                )

                if register:
                    register(
                        TransportOperationType.PUT,
                        '/{' + primary_key_name + '}/' + field.name,
                        getattr(manager_cls, put_a_field_handler_name),
                    )

        if get_a_field:
            if not get_a_field_options:
                raise ValueError('options are required for get_a_field')
            if not primary_key_field:
                raise ValueError('primary key is required for get_a_field')
            
            exec_namespaces = globals().copy()
            add_type_to_namespace(
                primary_key_field.vtype, exec_namespaces
            )
            
            fields = get_a_field_options.get('fields')
            for field in fields:

                get_a_field_handler_name = f'get_{field.name}'
                primary_key_name = f"{manager_name}_id"
                func_sig = f"async def {get_a_field_handler_name}(self, \n"
                func_sig += f"    {primary_key_name}: {primary_key_field.vtype.__name__}"
                func_sig += "):\n"
                func_body = f"    return await self._get_a_field(_id={primary_key_name}, \n"
                func_body += f"        field=self.scheme_cls.{field.in_scheme_name}\n"
                func_body += "    )\n"
                func_str = func_sig + func_body
                
                exec(func_str, exec_namespaces, result_namespaces)
                setattr(
                    manager_cls, get_a_field_handler_name, 
                    result_namespaces[get_a_field_handler_name]
                )

                if register:
                    register(
                        TransportOperationType.GET,
                        '/{' + primary_key_name + '}/' + field.name,
                        getattr(manager_cls, get_a_field_handler_name),
                    )

        if insert_item:
            if not insert_item_options:
                raise ValueError('options are required for insert_item')
            if not primary_key_field:
                raise ValueError('primary key is required for insert_item')
            
            exec_namespaces = globals().copy()
            add_type_to_namespace(
                primary_key_field.vtype, exec_namespaces
            )
            
            fields = insert_item_options.get('fields')
            for field in fields:
                insert_item_handler_name = f'insert_{field.name}'
                primary_key_name = f"{manager_name}_id"
                func_sig = f"async def {insert_item_handler_name}(self, body: typing.Sequence, \n"
                func_sig += f"{primary_key_name}: {primary_key_field.vtype.__name__},\n"
                func_sig += "at: typing.Optional[int] = None, mode: str = 'append',\n"
                func_sig += "):\n"
                func_body = f"    return await self._insert_item(_id={primary_key_name}, \n"
                func_body += f"        field=self.scheme_cls.{field.in_scheme_name},\n"
                func_body += "        mode=mode, at=at,\n"
                func_body += "        values=body\n"
                func_body += "    )\n"
                func_str = func_sig + func_body
                
                exec(func_str, exec_namespaces, result_namespaces)
                setattr(
                    manager_cls, insert_item_handler_name, 
                    result_namespaces[insert_item_handler_name]
                )

                if register:
                    register(
                        TransportOperationType.POST,
                        '/{' + primary_key_name + '}/' + field.name,
                        getattr(manager_cls, insert_item_handler_name),
                    )
        
        if delete_item:
            if not delete_item_options:
                raise ValueError('options are required for delete_item')
            if not primary_key_field:
                raise ValueError('primary key is required for delete_item')
            
            exec_namespaces = globals().copy()
            add_type_to_namespace(
                primary_key_field.vtype, exec_namespaces
            )
            
            fields = delete_item_options.get('fields')
            for field in fields:
                delete_item_handler_name = f'delete_{field.name}'
                primary_key_name = f"{manager_name}_id"
                func_sig = f"async def {delete_item_handler_name}(self, body: typing.Sequence, \n"
                func_sig += f"{primary_key_name}: {primary_key_field.vtype.__name__}"
                func_sig += "):\n"
                func_body = f"    return await self._delete_item(_id={primary_key_name}, \n"
                func_body += f"        field=self.scheme_cls.{field.in_scheme_name},\n"
                func_body += "        values=body\n"
                func_body += "    )\n"
                func_str = func_sig + func_body
                
                exec(func_str, exec_namespaces, result_namespaces)
                setattr(
                    manager_cls, delete_item_handler_name, 
                    result_namespaces[delete_item_handler_name]
                )

                if register:
                    register(
                        TransportOperationType.DELETE,
                        '/{' + primary_key_name + '}/' + field.name,
                        getattr(manager_cls, delete_item_handler_name),
                    )

        return manager_cls

    return wrapper

