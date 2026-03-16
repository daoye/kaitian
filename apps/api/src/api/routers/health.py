"""健康检查路由."""

from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])

@router.get("")
async def health_check():
    """健康检查端点."""
    return {"status": "ok", "service": "kaitian-api"}
