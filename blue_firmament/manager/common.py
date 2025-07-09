'''CommonManager Module
'''

__all__ = [
    "CommonManager", 
    "PresetHandlerConfig",
]

from dataclasses import dataclass
import typing
from typing import Literal as Lit, Optional as Opt

import event
from ..utils.exec_ import build_func_sig
from blue_firmament.task.registry import TaskRegistry
from blue_firmament.task.context.common import CommonTaskContext
from ..dal import KeyableType, DataAccessObject
from ..scheme.field import CompositeField, FieldValueProxy
from ..log.main import get_logger
# from .base import BaseFieldManager, 
from .base import BaseManager, SchemeTV
from ..utils.type import safe_issubclass
from ..utils.typing_ import safe_issubclass
from ..task.main import Method
from ..scheme import BaseScheme
from blue_firmament.task import TaskID

if typing.TYPE_CHECKING:
    from ..core.app import BlueFirmamentApp
    from ..scheme.field import Field


logger = get_logger(__name__)


@dataclass
class PresetHandlerConfig:
    """Config what and how preset handlers added to a manager.

    - These handlers will be automatically added to manager router.
      (which means their task_id's path are prefixed with the
      path_prefix you configured from class init params.)
    - You can call these handlers but without a type hinting.

    """

    editable: Opt[typing.Type[BaseScheme]] = None
    """Editable ver of managing scheme.

    This scheme is used to control which fields are editable
    for user. 
    
    Like in create, put and patch, forbids user from changing
    fields like id, created_at, but allows user modifying title,
    description...
    """
    sup_path: Opt[str] = None
    """Path append to the manager path prefix.
    
    If provided, handler's key param naming will be the same of this.
    """
    key_fields: Opt[dict[str, "Field"]] = None
    """Map key name to its field instance.

    For scheme only has one key, usually is not required.
    But for scheme has two or more (composite) keys, required.
    """
    get: bool = False
    """Add handler getting managing scheme.

    - Name: ``get_<manager_name>``
    - TaskID: ``GET /{<manager_name>_id}``
    """
    get_a_field: typing.Iterable["Field"] = ()
    """Add field getter handler for these fields.

    - Name: `get_<manager_name>_<field.name>`
    - TaskID: ``GET /{<manager_name>_id}/<field.name>``
    """
    create: bool = False
    """Add create handler.

    - Requiring editable
    """
    put: bool = False
    """
    
    - Requiring editable
    """
    put_a_field: typing.Iterable["Field"] = ()
    insert_item: typing.Iterable["Field"] = ()
    patch: bool = False
    """
    
    - Requiring editable
    """
    delete: bool = False
    delete_item: typing.Iterable["Field"] = ()


TV = typing.TypeVar('TV')
KeyTV = typing.TypeVar('KeyTV', bound=KeyableType)
class CommonManager(
    typing.Generic[SchemeTV, KeyTV],
    BaseManager[SchemeTV],
    CommonTaskContext,
):
    """
    Configuration
    -------------
    - scheme_cls: Scheme class this manager is managing
    - path_prefix: Path prefix of this manager's router.
    - manager_name: Friendly name of this manager.
        - use snake_case
    - preset_handler_config:
    """
    
    def __init_subclass__(
        cls,
        preset_handler_config: Opt[PresetHandlerConfig] = None,
        **kwargs
    ):
        super().__init_subclass__(**kwargs)
        scheme_cls = cls.__scheme_cls__
        manager_name = cls.__manager_name__

        if preset_handler_config:
            if not scheme_cls:
                raise ValueError("scheme cls is required if you want to set up \
                    preset handler")
            
            exec_namespaces = globals().copy()
            handlers: dict[str, typing.Callable] = {}

            key_field = scheme_cls.get_key_field()
            if isinstance(key_field, CompositeField) \
                and not preset_handler_config.key_fields:
                    raise ValueError("key fields required for composite key")

            
            key_aliases: typing.Iterable[str]
            if preset_handler_config.sup_path and preset_handler_config.key_fields:
                key_aliases = TaskID.resolve_dynamic_indices(
                    cls.__path_prefix__ + preset_handler_config.sup_path
                )
                sup_path = preset_handler_config.sup_path
                exec_namespaces.update({
                    f'{i}_conv': j.converter
                    for i, j in preset_handler_config.key_fields.items()
                })
            else:
                key_aliases = (f"{manager_name}_id",)
                sup_path = f"/{{{manager_name}_id}}"
                exec_namespaces[f"{key_aliases[0]}_conv"] = key_field.converter

            if preset_handler_config.get:
                handler_name = f'get_{manager_name}'
                func_sig = build_func_sig(
                    handler_name,
                    *(
                        (i, f"Anno[typing.Any, {i}_conv]")
                        for i in key_aliases
                    ),
                    async_=True,
                )
                if isinstance(key_field, CompositeField):
                    func_body = f"    return await self.get(_id={key_aliases[0]}_conv({ \
                        ",".join(
                            f"{preset_handler_config.key_fields[i].in_scheme_name}={i}" # type: ignore
                            for i in key_aliases
                        ) \
                    }))"
                else:
                    func_body = f"    return await self.get(_id={key_aliases[0]})"
                
                exec(func_sig + func_body, exec_namespaces, handlers)
                setattr(cls, handler_name, handlers[handler_name])

                cls.__task_registries__["default"].add_handler(
                    method=Method.GET, path=sup_path,
                    function=handlers[handler_name],
                    handler_manager_cls=cls
                )

    @property
    def _dao(self) -> DataAccessObject[SchemeTV]:
        """DAO of managing scheme.
        """
        return self._daos(self._scheme_cls)

    def _emit(
        self,
        name: str,
        parameters: Opt[dict] = None,
        metadata: Opt[dict] = None,
        without_prefix: bool = False
    ):
        """:meth:`event.simple_emit` but prefix name with manager path prefix.

        :param name: Name of event. Starts with dot.
        :param without_prefix:
            If True, do not prefix name with manager path prefix.
        """
        return event.simple_emit(
            name=f"{self.__path_prefix__.replace('/', '.') if not without_prefix else ""}{name}",
            parameters=parameters,
            metadata=metadata
        )
    
    async def _get_scheme(self, _id: Opt[KeyTV] = None) -> SchemeTV:
        
        """Get managing scheme.

        :param _id: Key value

            If not None, return a scheme which key matches _id value;
            otherwise return the managing scheme.

        :raise ValueError: no managing scheme and _id is None

        Examples
        --------
        .. code-block:: python
            class MyManager(CommonManager[My, KeyType]):
                ...
                async def my_handler(self, _id: Opt[IdType] = None):
                    my = await self._get_scheme(_id)
        """
        try:
            scheme = self._scheme

            if _id is not None:
                if scheme.key_value == _id:
                    return scheme
                raise ValueError
            return scheme
        except ValueError as e:
            if _id is not None:
                return await self.get(_id=_id)
            raise e
    
    async def get(self, _id: KeyTV) -> SchemeTV:
        
        """Get scheme

        If success, set as managing scheme.
        """
        self._scheme = await self._dao.select_one(
            _id, task_context=self
        )
        return self._scheme
    
    async def insert(self, 
        scheme: Opt[SchemeTV] = None,
    ) -> SchemeTV:
        """插入数据模型实例到 DAO

        - 插入成功则设置为当前实例
        
        :param scheme: 数据模型实例；不提供则为当前实例

        """
        self._scheme = await self._dao.insert(
            to_insert=scheme or await self._get_scheme(),
        )
        return self._scheme
    
    async def _update_scheme(self,
        scheme: Opt[SchemeTV] = None,
    ) -> SchemeTV:
        """Update dirty fields to dal.

        If success, set update result to manager scheme.
        """
        self._scheme = await self._dao.update(
            to_update=scheme or await self._get_scheme(), 
            only_dirty=True,
        )
        return self._scheme

    async def get_a_field(self, 
        field: "Field[TV]", 
        _id: Opt[KeyTV] = None,
    ) -> TV:
        """Get a field's value of managing scheme.

        :returns: Field Value (no proxy)
        """
        scheme = self._try_get_scheme()
        if not scheme:
            return await self._dao.select_one(
                self._scheme_cls.get_key_field().equals(_id),
                field=field, 
                task_context=self
            )
        else:
            return FieldValueProxy.dump(scheme._get_value(field))
        
    async def put_a_field(self, 
        field: "Field[TV]", 
        value: TV,  
        _id: Opt[KeyTV] = None,
    ) -> TV:
        
        """Put a field value of managing scheme.

        Put value will be performed on scheme so that
        related validators can be run, and then
        patch to dal.
        """        
        scheme = await self._get_scheme(_id=_id)
        scheme[field] = value
        return (await self._update_scheme(scheme))[field]

    IoDableT = typing.TypeVar('IoDableT', bound=typing.List | typing.Set)
    async def insert_item(self, 
        field: "Field[IoDableT]",
        values: typing.Iterable[TV],
        _id: Opt[KeyTV] = None,
        mode: Lit['append', 'prepend', 'insert'] = 'append',
        at: Opt[int] = None,
    ) -> IoDableT:
        
        """插入条目到列表型字段值

        :param _id: 主键值；没有则从当前实例获取
        :param field: 要插入到的字段；类型必须是列表或集合
        :param values: 要插入的值（可多个）；
        :param mode: 插入模式 （Set 不生效）

            - append: `[raw][values]`
            - prepend: `[values][raw]`
            - insert: `[raw before at][values][raw after at]`
        :param at: 插入位置；仅当 mode 为 `insert`
        """
        field_value = await self.get_a_field(_id=_id, field=field) 

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
        elif isinstance(field_value, set):
            field_value.update(values)
        else:
            raise ValueError(f'DAO not returning valid value of field {field}, {field_value}')
        
        return await self.put_a_field(
            field=field, value=field_value, 
            _id=_id,
        )
    
    async def delete_item(self, 
        field: "Field[IoDableT]", 
        values: typing.Union[
            typing.Iterable[TV],
            typing.Set[TV]
        ],
        _id: Opt[KeyTV] = None,
    ) -> IoDableT:
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
        field_value = await self.get_a_field(_id=_id, field=field)

        if isinstance(values, (list,)):
            field_value = [v for v in field_value if v not in values]
        elif isinstance(values, (set,)):
            for value in values:
                field_value.remove(value)
        else:
            raise ValueError(f'{field} value invalid, value is {field_value}')

        return await self.put_a_field(
            _id=_id, field=field, value=field_value
        )
    
    async def delete(self, _id: Opt[KeyTV] = None) -> None:
        """Delete the scheme from DAO

        If success, set managing scheme to None.

        :param _id: key value

            If not provided, use managing scheme's.
        """
        scheme = await self._get_scheme(_id=_id)
        await self._dao.delete(scheme)
        self._reset_scheme()


# CommonManagerTV = typing.TypeVar('CommonManagerTV', bound=CommonManager)
# class CommonFieldManager(
#     typing.Generic[TV, KeyTV, CommonManagerTV],
#     BaseFieldManager[TV, CommonManagerTV]
# ):
    
#     __scheme_manager_cls__: typing.Type[CommonManagerTV]

#     async def get_field(self,
#         _id: Opt[KeyTV] = None
#     ) -> TV:
        
#         """获取字段值
#         """
#         if self._field_value is None:
#             scheme = await self.scheme_manager._get_scheme(_id=_id)
#             self._field_value = scheme[self.field]
        
#         return typing.cast(TV, self._field_value)
    
#     async def update_field(self,
#         _id: Opt[KeyTV] = None,
#         value: TV | Undefined = _undefined
#     ) -> TV:
        
#         """更新字段值
#         """
#         if value is _undefined:
#             value_ = self._field_value
#         else:
#             value_ = value
        
#         scheme = await self.scheme_manager._get_scheme(_id=_id)
#         scheme[self.field] = value_
#         return await self._mdao.update(scheme)

class GetAFieldOptions(typing.TypedDict):
    fields: typing.Iterable["Field"]

class CreateOptions(typing.TypedDict):
    disabled_fields: typing.Iterable["Field"]

class InsertItemOptions(typing.TypedDict):
    fields: typing.Iterable["Field"]

class DeleteItemOptions(typing.TypedDict):
    fields: typing.Iterable["Field"]

class PatchOptions(typing.TypedDict):
    available_fields: typing.Iterable["Field"]

class PutAFieldOptions(typing.TypedDict):
    fields: typing.Iterable["Field"]

class PutOptions(typing.TypedDict):
    disabled_fields: typing.Iterable["Field"]


ManagerType = typing.TypeVar('ManagerType', bound=CommonManager)
def common_handler_adder(
    path_prefix_with_key: Opt[str] = None,
    get: bool = False,  # TODO 添加鉴权器（防御式）
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

        manager_name = manager_cls.__manager_name__
        primary_key_name = manager_name + "_id"
        if path_prefix_with_key is None:
            path_prefix_with_key_ = f"{manager_name}/{{{primary_key_name}}}"
        else:
            path_prefix_with_key_ = path_prefix_with_key

        if app:
            register = manager_cls.get_route_register(app)
        else:
            register = None

        if safe_issubclass(manager_cls.__scheme_cls__, BaseScheme):
            primary_key_field = manager_cls.__scheme_cls__.get_key_field()
        else:
            primary_key_field = None

        result_namespaces = {}

        if get:
            if not primary_key_field:
                raise ValueError('primary key is required for get')
            
            exec_namespaces = globals().copy()
            
            get_handler_name = f'get_{manager_name}'
            func_sig = f"async def {get_handler_name}(self, \n"
            if isinstance(primary_key_field, CompositeField):
                exec_namespaces[f'{primary_key_name}'] = primary_key_field.vtype
                for i in primary_key_field.sub_fields:
                    exec_namespaces[f"{i.name}_validator"] = i.converter
                    func_sig += f"{i.name}: typing.Annotated[typing.Any, {i.name}_validator],"
                func_body = f"    return await self.get(_id={primary_key_name}({
                    f",".join(
                        f"{i.name}={i.name}"
                        for i in primary_key_field.sub_fields
                    )
                }))"
            else:
                exec_namespaces["pk_validator"] = primary_key_field.converter
                func_sig += f"{primary_key_name}: typing.Annotated[typing.Any, pk_validator]"
                func_body = f"    return await self.get(_id={primary_key_name})"
            func_sig += "):\n"
            func_str = func_sig + func_body
            
            exec(func_str, exec_namespaces, result_namespaces)
            setattr(
                manager_cls, get_handler_name, 
                result_namespaces[get_handler_name]
            )

            if app:
                app.task_registry.add_handler(
                    method=Method.GET,
                    path=path_prefix_with_key_,
                    handler=getattr(manager_cls, get_handler_name),
                    handler_manager_cls=manager_cls
                )

        if put_a_field:
            if not put_a_field_options:
                raise ValueError('options are required for put_a_field')
            if not primary_key_field:
                raise ValueError('primary key is required for put_a_field')
            
            exec_namespaces = globals().copy()
            exec_namespaces["pk_validator"] = primary_key_field.converter
            
            fields = put_a_field_options.get('fields')
            for field in fields:

                put_a_field_handler_name = f'put_{field.name}'
                primary_key_name = f"{manager_name}_id"
                func_sig = f"async def {put_a_field_handler_name}(self, body, \n"
                func_sig += f"{primary_key_name}: typing.Annotated[typing.Any, pk_validator]"
                func_sig += "):\n"
                func_body = f"    return await self.put_a_field(_id={primary_key_name},\n"
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
                        Method.PUT,
                        '/{' + primary_key_name + '}/' + field.name,
                        getattr(manager_cls, put_a_field_handler_name),
                    )

        if get_a_field:
            if not get_a_field_options:
                raise ValueError('options are required for get_a_field')
            if not primary_key_field:
                raise ValueError('primary key is required for get_a_field')
            
            exec_namespaces = globals().copy()
            exec_namespaces["pk_validator"] = primary_key_field.converter
            
            fields = get_a_field_options.get('fields')
            for field in fields:

                get_a_field_handler_name = f'get_{field.name}'
                primary_key_name = f"{manager_name}_id"
                func_sig = f"async def {get_a_field_handler_name}(self, \n"
                func_sig += f"    {primary_key_name}: typing.Annotated[typing.Any, pk_validator]"
                func_sig += "):\n"
                func_body = f"    return await self.get_a_field(_id={primary_key_name}, \n"
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
                        Method.GET,
                        '/{' + primary_key_name + '}/' + field.name,
                        getattr(manager_cls, get_a_field_handler_name),
                    )

        if insert_item:
            if not insert_item_options:
                raise ValueError('options are required for insert_item')
            if not primary_key_field:
                raise ValueError('primary key is required for insert_item')
            
            exec_namespaces = globals().copy()
            exec_namespaces["pk_validator"] = primary_key_field.converter
            
            fields = insert_item_options.get('fields')
            for field in fields:
                insert_item_handler_name = f'insert_{field.name}'
                primary_key_name = f"{manager_name}_id"
                func_sig = f"async def {insert_item_handler_name}(self, body: typing.Sequence, \n"
                func_sig += f"{primary_key_name}: typing.Annotated[typing.Any, pk_validator],\n"
                func_sig += "at: typing.Optional[int] = None, mode: str = 'append',\n"
                func_sig += "):\n"
                func_body = f"    return await self.insert_item(_id={primary_key_name}, \n"
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
                        Method.POST,
                        '/{' + primary_key_name + '}/' + field.name,
                        getattr(manager_cls, insert_item_handler_name),
                    )
        
        if delete_item:
            if not delete_item_options:
                raise ValueError('options are required for delete_item')
            if not primary_key_field:
                raise ValueError('primary key is required for delete_item')
            
            exec_namespaces = globals().copy()
            exec_namespaces["pk_validator"] = primary_key_field.converter
            
            fields = delete_item_options.get('fields')
            for field in fields:
                delete_item_handler_name = f'delete_{field.name}'
                primary_key_name = f"{manager_name}_id"
                func_sig = f"async def {delete_item_handler_name}(self, body: typing.Sequence, \n"
                func_sig += f"{primary_key_name}: typing.Annotated[typing.Any, pk_validator],\n"
                func_sig += "):\n"
                func_body = f"    return await self.delete_item(_id={primary_key_name}, \n"
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
                        Method.DELETE,
                        '/{' + primary_key_name + '}/' + field.name,
                        getattr(manager_cls, delete_item_handler_name),
                    )

        return manager_cls

    return wrapper

