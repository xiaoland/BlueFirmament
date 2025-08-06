"""Utils for handlers."""

__all__ = [
    "retry"
]

import typing
import time

from .main import call_as_async
from ..exceptions import Retryable, MaxRetriesExceeded


def retry(
    max_: int = 1,
    default_delay: int | float = 0.2,
):
    """Retry decorated function when it raises a retryable exception.

    :param max_: The maximum number of retries
    :param default_delay: The delay between retries in seconds if
        Retryable exception does not specify a delay.

    Async and sync functions are supported and all call as async.

    Examples
    ^^^^^^^^
    ..code-block:: python
        from blue_firmament.utils.handler_ import retry
        from blue_firmament.exceptions import Retryable

        @retry()
        def your_function(a, b: int = 1):
            ... do something ...
            if some_condition:
                # recover state and prepare for retry, like refreshing token
                raise Retryable(delay=0.2)
    """
    def decorator(func: typing.Callable):
        async def wrapper(*args, **kwargs):
            for attempt in range(max_+1):
                try:
                    return await call_as_async(func, *args, **kwargs)
                except Retryable as e:
                    time.sleep(e.delay or default_delay)

            raise MaxRetriesExceeded()

        return wrapper

    return decorator