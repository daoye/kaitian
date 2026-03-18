"""重试工具模块.

提供简单的重试机制，用于处理瞬态故障。
"""

import asyncio
from functools import wraps
from typing import Any, Callable, TypeVar

from .exceptions import BrowserError

T = TypeVar("T")


def retry(
    max_attempts: int = 3,
    delay_ms: float = 100,
    backoff: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """重试装饰器.

    Args:
        max_attempts: 最大重试次数（包含首次尝试）
        delay_ms: 初始延迟（毫秒）
        backoff: 退避系数
        exceptions: 需要重试的异常类型

    Returns:
        装饰器函数
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Exception | None = None
            current_delay = delay_ms / 1000  # 转换为秒

            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts:
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        break

            raise last_exception or BrowserError("max retry attempts exceeded")

        return wrapper

    return decorator
