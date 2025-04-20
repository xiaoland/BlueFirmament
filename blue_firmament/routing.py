'''Route request from transport layer to correct handlers'''

import typing
import inspect

from .transport.request import Request
from .transport import TransportOperationType
from .scheme.validator import AnyValidator, BaseValidator, get_validator_by_type
from .scheme import BaseScheme
from .utils.type import (
    is_annotated, get_origin, is_json_dumpable, safe_issubclass
)
from .utils import call_function_as_async
from .middleware import BaseMiddleware
from .manager import BaseManager
from .transport.response import Response, JsonResponseBody


PathParamsType = typing.Dict[str, typing.Any]
RequestHandlerType = typing.Union[
    typing.Callable[..., typing.Any],
    typing.Callable[..., typing.Awaitable[typing.Any]]
]
HANDLER_BODY_KW = 'body'
class RequestHandlerEnv(typing.TypedDict):
    
    """请求处理器环境
    """
    request: Request
    response: Response
    path_params: PathParamsType

RouteKeyParamTypesType = typing.TypeVar('RouteKeyParamTypesType', bound=typing.Dict[str, typing.Type])
class RouteKey(typing.Generic[RouteKeyParamTypesType]):

    """碧霄路由键

    路由键由操作和路径组成，作为路由记录的键。

    操作
    ^^^^
    > 支持的操作请参考：`BlueFirmamentOperationType`

    - 如果操作为None，则表示通配

    路径
    ^^^^
    - 路径可以含有参数，使用花括号包裹（例如，'/users/{id}'）
    - 路径参数只可以通过位置匹配，但可以具有名称
    - 路径参数可以配置类型，如果类型不匹配，路由不会匹配
    """

    def __init__(
        self, operation: typing.Optional[TransportOperationType], raw_path: str,
        param_types: RouteKeyParamTypesType = {},
        param_validators: typing.Optional[typing.Dict[str, BaseValidator]] = None
    ):
        
        """
        Parameters
        ----------
        - `operation`: operation supported by BlueFirmament；None is wildcard
        - `path`: A URL-like path, which can include parameters (e.g., '/users/{id}', 'users', 'users/')
        - `param_types`: A dictionary of parameter names and their types
        - `param_validators`: 参数的校验器映射表；如果未提供，自动从`param_types`推断
        """
        
        self._operation = operation
        self._path = raw_path.strip('/')
        
        self.__segments: typing.List[str] = raw_path.strip('/').split('/')
        '''Parse path into segments'''
        self.__param_indices: typing.Iterable[int] = [i for i, segment in enumerate(self.__segments) if segment.startswith('{') and segment.endswith('}')]
        '''Record parameters (wrapped by curly braces)'s index'''
        self.__static_indices: typing.Iterable[int] = set(range(len(self.__segments))) - set(self.__param_indices)
        '''Record static segments'''
        if typing.TYPE_CHECKING:
            self.__param_validators: typing.Dict[str, BaseValidator]
            '''参数名称及其对应的校验器
            
            - 一定有所有参数的校验器
            - 如果参数没有指定类型，则使用通用校验器（AnyValidator）
            '''
        
        if not param_validators:
            self.__param_validators = {
                param_name: get_validator_by_type(param_types[param_name]) if param_name in param_types else AnyValidator()
                for param_name in [
                    self.__get_param_name(self.__segments[i]) for i in self.__param_indices
                ] 
            }
        else:
            self.__param_validators = param_validators
        
    def __eq__(self, other):

        '''严格比较两个路由键
        '''
        if other is None:
            return False
        if not isinstance(other, RouteKey):
            return False
        return (self.is_match(other, True))[0]
        

    def __hash__(self):
        return hash((self.operation, *(i for i in self.segments)))
    
    def __str__(self):
        return f"{self.operation} {self.path}"
    
    def __len__(self) -> int:
        return len(self.segments)
    
    def __getitem__(self, key) -> 'RouteKey':

        '''
        使用slice获取子路由键
        '''
        if isinstance(key, slice):
            return RouteKey(self._operation, '/'.join(self.__segments[key]), param_validators=self.__param_validators)
        else:
            return RouteKey(self._operation, self.__segments[key], param_validators=self.__param_validators)
    
    def __is_segment_match(self, other: str, segment_index: int) -> typing.Tuple[bool, typing.Any | None]:
        
        """检查一个分段是否匹配
        
        传入分段及下标，这个分段可以是静态的，也可以是参数分段。\n
        如果是静态分段，直接作`__equal__`比较，\n
        如果是动态分段，调用参数的校验器，如果通过则返回True，否则返回False。

        Parameters
        ----------
        - `other`: 被比较的分段；必须和`segment_index`对应
        - `segment_index`: 分段的下标

        Returns
        -------
        返回一个元组，第一个元素是是否匹配，第二个元素是校验结果；\n
        第二个元素仅在动态分段且匹配时有值，如果是静态分段则为None。
        """
        if segment_index in self.__static_indices:
            return self.segments[segment_index] == other, None
        elif segment_index in self.__param_indices:
            param_name = self.__get_param_name(self.segments[segment_index])
            param_validator = self.__param_validators[param_name]  # 不可能发生KeyError
            try:
                res = param_validator(other)
                return True, res
            except ValueError:
                return False, None
        else:
            return False, None
    
    @property
    def operation(self) -> typing.Optional[TransportOperationType]:
        return self._operation

    @property
    def path(self) -> str:

        '''路径字符串
        
        不一定初始化时相等，但一定会是 ``'/' + raw_path.strip('/') + '/'``
        '''
        return f"/{self._path}/"
    
    @property
    def segments(self) -> typing.List[str]:
        return self.__segments
    
    @property
    def has_parameters(self) -> bool:
        return bool(self.__param_indices)
    
    @staticmethod
    def __get_param_name(segment: str) -> str:

        '''从动态分段取得参数名
        
        前提：确保该分段是动态分段
        '''
        return segment[1:-1]
    
    def resolve_params(self, segments: typing.List[str]) -> RouteKeyParamTypesType:
        
        """解析参数
        
        传入分段列表，返回符合本路由键参数定义的参数解析结果。

        一般在使用 ``__eq__`` 匹配路由成功后解析参数。

        Parameters
        ^^^
        - `segments`: 分段列表

        Returns
        ^^^
        - 字典键一定包含本路由键定义的所有参数
        - 如果参数校验不通过或不存在，则为None

        Tests
        ^^^
        - `test_routing.TestRouteKey.test_resolve_params`
        """
        result = {}
        
        for i in self.__param_indices:
            param_name = self.__get_param_name(self.__segments[i])
            try:
                param_validator = self.__param_validators[param_name]
                result[param_name] = param_validator(segments[i])
            except (IndexError, KeyError, ValueError):
                # IndexError: 我方不存在对应的分段
                # KeyError: 没有对应的参数校验器
                # ValueError: 校验不通过
                result[param_name] = None
        
        return typing.cast(RouteKeyParamTypesType, result)
    
    def is_match(
        self, other: 'RouteKey', strict: bool = False
    ) -> typing.Tuple[
        bool, typing.Dict[str, typing.Any] | None
    ]:
        
        """检查是否匹配
        
        传入一个路由键，检查是否与本路由键匹配。（不要求完全匹配，只要我方是对方的子集即可）

        Implementation
        ^^^^^^^^^^^^^^^
        - 检查操作
            - 如果操作是通配的，则无需检查操作是否匹配
        - 检查路径
            - 如果路径分段数量小于本路由键，则不匹配（严格模式下要求长度一致）
            - 如果没有路径参数，比较我方路径分段（仅静态）是否为对方的子集（严格模式比较路径字符串）
            - 如果有路径参数，比较我方路径分段（包括静态与动态）是否为对方的子集（严格模式检验对方是否为我方子集）
              - 此处解析路径参数，如果未找到或校验不通过，则不记录

        :param other: 另一个路由键
        :param strict: 是否严格匹配；严格匹配即完全匹配
        
        Returns
        ^^^
        - 匹配时返回True和参数解析结果
            - 参数解析结果仅包括存在的、有效的
        - 不匹配时返回False和None

        Tests
        ^^^
        - `test_routing.TestRouteKey.test_is_match`
        """
        if not isinstance(other, RouteKey):
            return False, None
        
        if self.operation:
            if self.operation != other.operation:
                return False, None
        
        if not strict:
            if len(self.segments) > len(other.segments):
                return False, None
        else:
            if len(self.segments) != len(other.segments):
                return False, None
            
        if not self.has_parameters:
            if not strict:
                for i, segment in enumerate(self.segments):
                    if segment != other.segments[i]:
                        return False, None
                
                return True, None
            else:
                return self.path == other.path, None
        
        params = {}
        for i in range(len(self.segments if not strict else other.segments)):
            seg_match = self.__is_segment_match(other.segments[i], i)
            if seg_match[0] is False:
                return False, None
            else:
                if seg_match[1] is not None:
                    params[self.__get_param_name(self.segments[i])] = seg_match[1]

        return True, params


class RouteRecord(BaseMiddleware):
    
    """碧霄路由记录（中间件）

    路由记录将路由键映射到一个请求处理器或另一个路由器。路由记录被保存在路由器中，用于路由请求。
    """

    HandlerKwargsType = typing.Dict[str, typing.Callable[[RequestHandlerEnv], typing.Any]]
    TargetType = typing.Union[RequestHandlerType, 'Router']
    
    def __init__(self, 
        key: RouteKey, value: TargetType,
        handler_manager: typing.Optional[typing.Type[BaseManager]] = None,
    ):

        """
        Initialize a route record.
        
        Parameters
        ----------
        - `route_key`: The route key that this record matches
        - `target`: Either a handler function or another router that processes the request
        - `handler_manager`: If the target is a manager method, this is the manager class. 
        
        handler_manager
        ^^^^^^^^^^^^^^
        Static method and class method is not counted as a handler on manager.
        Only `Class.method` is counted.
        """
        self.__route_key = key
        self.__target = value
        self.__method_manager_cls = handler_manager

        # parse handler kwargs
        self.__handler_kwargs: RouteRecord.HandlerKwargsType = {}
        if not isinstance(self.__target, Router):
            self.__handler_kwargs = self.parse_handler_kwargs(self.__target)

    @property
    def route_key(self) -> RouteKey:
        return self.__route_key
    
    @property
    def target(self) -> TargetType:
        return self.__target
            
    
    def __hash__(self) -> int:
        return hash(self.__route_key)
    
    def __eq__(self, value) -> bool:
        
        '''
        如果是RouteKey，则直接与route_key比较；如果是RouteRecord，则比较route_key是否相等。
        '''
        if isinstance(value, RouteKey):
            return self.__route_key == value
        elif isinstance(value, RouteRecord):
            return self.__route_key == value.__route_key
        return False    
    
    @property
    def is_mapping_to_router(self) -> bool:
        """Check if this route record points to another router"""
        return isinstance(self.__target, Router)
    
    def is_key_match(self, route_key: RouteKey):
        
        """判断路由键是否匹配        
        """
        return self.__route_key.is_match(route_key)
    
    @staticmethod
    def __get_path_query_param_getter(key: str, validator: BaseValidator):

        """获取路径参数或查询参数的获取器
        
        传入参数名称和校验器，返回一个获取器函数用以按照名称和类型从path, query_params中解析参数
        """
        def get_path_query_param(env: RequestHandlerEnv):

            try:
                return validator(env['path_params'][key])
            except KeyError:
                try:
                    return validator(env['request'].query_params[key])
                except KeyError:
                    raise ValueError(f'{key} not found in path or query params')
        
        return get_path_query_param
    
    @staticmethod
    def __get_body_getter1(validator: typing.Type[BaseScheme]):

        """获取一类请求体参数获取器

        一类：BaseScheme
        """
        def get_body_1(env: RequestHandlerEnv):
            request = env['request']
            if isinstance(request.body, dict):
                return validator(**request.body)
            else:
                raise ValueError('body must be dict')
            
        return get_body_1
    
    @staticmethod
    def __get_body_getter2(validator: BaseValidator):

        """获取二类请求体参数获取器

        二类：原样
        """
        def get_body_2(env: RequestHandlerEnv):
            request = env['request']
            return validator(request.body)
        
        return get_body_2
        
    
    @classmethod
    def parse_handler_kwargs(cls, handler: RequestHandlerType) -> HandlerKwargsType:

        '''解析处理器参数

        Rationale
        ---------
        - 此处假设处理器的签名是静态的，所以可以在路由记录实例化时解析参数备用，无需每次调用处理器之前重新解析
        - ``__call__`` 等调用处理器时将会

        Behaviour
        ----------
        参数解析规则
        ^^^^^^^^^^^^^^^
        - 跳过这些名称的参数
            - `self`, `cls`
        - 基于类型解析系统信息
            - `Response`, `Request`
        - 基于名称解析请求体参数（只能有一个，名称为 `HANDLER_BODY_KW` ）
        - 基于名称和类型解析路径参数、查询参数
            - 路径参数优先于查询参数
            - 名称匹配但类型不匹配会导致 `ValueError` 异常

        参数类型读取
        ^^^^^^^^^^^^^^
        - 通过 `inspect.signature().parameters` 获取参数列表
        - 通过 `utils.type.get_origin(params['param_name'])` 获取参数的类型 \n
          从而兼容 `typing.Annotated` 和 `typing.NewType` 等非直接类型标注
        - 当使用 `typing.Annotated` 时，元数据[0]会被用作校验器/转换器 \n
          其他情况则使用 `scheme.validator.get_validator_by_type` 根据类型校验器/转换器

        Dependency
        -----------
        - `scheme.validator.get_validator_by_type`
        - `utils.type.get_origin`

        Returns
        -------
        返回一个字典，键为处理器的参数名称，值为该参数的获取器。

        参数获取器接收 `RequestHandlerEnv` 作为参数，从中解析出本参数需要的值。
        '''
        handler_params = inspect.signature(handler).parameters
        kwargs: RouteRecord.HandlerKwargsType = {}

        for key, param in handler_params.items():

            if key in ('self', 'cls'):
                continue
            
            anno = get_origin(param.annotation) 
            if is_annotated(param.annotation): 
                validator = param.annotation.__metadata__[0]
            else:
                validator = get_validator_by_type(anno)

            if safe_issubclass(anno, Request):
                kwargs[key] = lambda env: env['request']
                continue
            elif safe_issubclass(anno, Response):
                kwargs[key] = lambda env: env['response']
                continue
            
            if key == HANDLER_BODY_KW:
                if safe_issubclass(anno, BaseScheme):
                    if not safe_issubclass(validator, BaseScheme):
                        raise TypeError('When annotation is BaseScheme, the validator (typing.Annotated arg 1) must be BaseScheme too')
                    
                    kwargs[HANDLER_BODY_KW] = cls.__get_body_getter1(validator)
                else:
                    kwargs[HANDLER_BODY_KW] = cls.__get_body_getter2(validator)

                continue

            kwargs[key] = cls.__get_path_query_param_getter(key, validator)

        return kwargs
    
    async def __call__(self, *,
        next,
        request: "Request", 
        response: "Response",
        path_params: PathParamsType = {},
        **kwargs
    ):
        
        if isinstance(self.__target, Router):
            self.__target()  # type: ignore  调用不了自然报错
            next()
        else:
            await self.execute_handler(request, response, path_params)
            next()
        

    async def execute_handler(self, 
        request: "Request", 
        response: "Response",
        path_params: PathParamsType = {},
    ):

        """调用处理器（中间件）

        :path_params: 路径参数；如果没有路径参数，则为空字典（不要修改之）

        Behaviour
        ---------
        - 自动传递参数：基于实例化时解析的 `RequestHandlerKwargs`，从环境中解析出参数
        - 自动处理异步/同步函数：通过 `inspect.iscoroutinefunction` 判断函数是否为异步函数
        - 自动处理返回值：处理器的返回值会被解析到响应对象中

        自动处理返回值
        ^^^^^^^^^^^^^^^^
        - 如果处理器返回值是字典，则将其转换为JSON响应体

        
        """
        assert not isinstance(self.__target, Router), "Target is not handler."
        
        # get kwargs
        env: RequestHandlerEnv = {
            'request': request,
            'response': response,
            'path_params': path_params
        }
        kwargs = {key: getter(env) for key, getter in self.__handler_kwargs.items()}

        # get args
        args = []
        # [self] don't add other arg parser before this one
        if self.__method_manager_cls:
            manager = self.__method_manager_cls(request.session)
            args.append(manager)

        # call handler
        result = await call_function_as_async(self.__target, *args, **kwargs)

        # process result
        # TODO process result correctly
        if is_json_dumpable(result):
            response.body = JsonResponseBody(result)
        else:
            # TODO
            response.body = JsonResponseBody({'error': 'Invalid response type'})
    

class Router:

    """碧霄路由器
    
    A router is a collection of route records that map route keys to handlers or other routers.
    This organization allows for building complex routing networks by nesting routers.
    
    Examples:
    - API versioning: /api/v1/* routes to v1Router, /api/v2/* routes to v2Router
    - Resource organization: /users/* routes to userRouter, /products/* routes to productRouter
    - Middleware chains: authenticated routes can be organized under an auth router

    效率优化
    ^^^^^^^^
    - 铺平（信息总量不变，但是一个节点拥有的信息越多，就降低了与其它节点交换信息带来的效率损耗）
    """

    def __init__(self, name: str = 'router'):
        # Regular routes map exact route keys to records
        self.__records: typing.List[RouteRecord] = []
        
        self.__name = name

    @property
    def name(self): return self.__name
        
    def add_route_record(
        self, operation: TransportOperationType, path: str, 
        handler: RequestHandlerType | 'Router',
        handler_manager: typing.Optional[typing.Type[BaseManager]] = None
    ):
        
        """
        Add a route record to this router.
        
                                                                                                                                               
        :param operation: The operation type (GET, POST, etc.)
        :param path: A URL-like path, which can include parameters (e.g., '/users/{id}')
        :param handler: Either a handler function that processes the request,
                              or another router that continues the routing process
        """
        route_key = RouteKey(operation, path)
        record = RouteRecord(route_key, handler, handler_manager)
        
        self.__records.append(record)

    def routing(
        self, route_key: RouteKey, leaf_node: bool = True
    ) -> typing.Tuple[RouteRecord, typing.Optional[PathParamsType]]:
        
        """为一个路由键在本路由中找到匹配的路由记录并解析参数
        
        :param route_key: 待匹配的路由键
        :param leave_node: 是否返回叶节点（否则在找到一个匹配的记录之后就返回）

        Returns
        --------
        返回一个元组。

        第一个元素为匹配的路由记录 \n
        第二个元素为参数解析结果，如果没有参数则返回None。

        Exceptions
        -----------
        如果找不到匹配的记录，则抛出`KeyError`异常
        """
        if not leaf_node:
            for record in self.__records:
                is_match, params = record.is_key_match(route_key)
                if is_match:
                    return record, params
        else:
            params = {}

            for record in self.__records:
                is_match, sub_params = record.is_key_match(route_key)
                if is_match:
                    if sub_params:
                        params.update(sub_params)
                    
                    if record.is_mapping_to_router:
                        new_route_key = route_key[len(record.route_key):]
                        record, sub_params = typing.cast(
                            Router, record.target
                        ).routing(
                            new_route_key, leaf_node
                        )

                        if sub_params:
                            params.update(sub_params)

                        return record, params
                    else:
                        # is fully match (leaf node must be fully matched)
                        if len(route_key) == len(record.route_key):
                            return record, params or None
                        continue

        raise KeyError(f"Route key {route_key} not matching a record in router {self.name}")

    def get_manager_handler_route_record_register(self,
        manager: typing.Type[BaseManager], path_prefix: str = '',
        use_manager_prefix: bool = True,
    ) -> typing.Callable[
        [TransportOperationType, str, RequestHandlerType], None
    ]:
        
        '''获取管理器处理器的路由注册器

        省去了 ``add_route_record`` 的 ``handler_manager`` 参数，并提供了一个路径前缀

        :param manager: 管理器类
        :param path_prefix: 路径前缀
        :param use_manager_name_as_prefix: 是否使用管理器配置的路径前缀
        '''
        def add_route_record(
            operation: TransportOperationType, path: str,
            handler: RequestHandlerType
        ):
            
            if use_manager_prefix and not path_prefix:
                path = f'/{manager.__path_prefix__}{path}'
            elif path_prefix:
                path = f'/{path_prefix}{path}'
            
            self.add_route_record(operation, path, handler, manager)

        return add_route_record

