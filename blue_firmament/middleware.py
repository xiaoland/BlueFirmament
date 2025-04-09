'''Blue Firmament Middleware'''

import abc
import typing


NextType = typing.Callable[[], None]

class BaseMiddleware(abc.ABC):

    '''碧霄中间件基类
    '''

    MiddlewaresType = typing.Tuple['BaseMiddleware', ...]

    @abc.abstractmethod
    def __call__(self, *, next: NextType, **kwargs) -> typing.Union[
        None, typing.Coroutine
    ]:
        pass

    @staticmethod
    def get_next(middwares: MiddlewaresType, **kwargs) -> NextType:

        """获取下一个中间件的调用函数
        
        :param middwares: 中间件列表
        :param kwargs: 传递给中间件的关键字参数
        """
        
        current: int = 0
        def next() -> None:
            nonlocal current
            current += 1
            if current < len(middwares):
                middwares[current].__call__(next=next, **kwargs)
            else:
                return None
        
        return next
