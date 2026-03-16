"""数据模型模块."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """健康检查响应模型."""
    
    status: str
    service: str


class RootResponse(BaseModel):
    """根端点响应模型."""
    
    name: str
    version: str
    docs: str