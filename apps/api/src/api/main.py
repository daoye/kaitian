"""FastAPI 应用入口."""

from fastapi import FastAPI

from api.routers import health

app = FastAPI(
    title="KaiTian API",
    description="KaiTian 模块化采集工具 API",
    version="0.1.0",
)

app.include_router(health.router)

@app.get("/")
async def root():
    """根端点."""
    return {
        "name": "KaiTian API",
        "version": "0.1.0",
        "docs": "/docs",
    }
