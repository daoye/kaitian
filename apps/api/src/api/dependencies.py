"""依赖注入模块."""

from typing import Annotated, AsyncGenerator

from fastapi import Depends


async def get_db() -> AsyncGenerator[None, None]:
    """获取数据库会话."""
    yield


# 常用依赖项
CommonDepends = Annotated[None, Depends(get_db)]
