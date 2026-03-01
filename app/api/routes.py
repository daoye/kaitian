"""API routes for KaiTian application."""

from fastapi import APIRouter, HTTPException
from datetime import datetime
from app.models.schemas import HealthCheckResponse
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1", tags=["api"])


@router.get("/health", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    """Health check endpoint."""
    settings = get_settings()
    return HealthCheckResponse(
        status="ok",
        version=settings.app_version,
        timestamp=datetime.utcnow(),
    )


@router.get("/")
async def root():
    """Root endpoint."""
    settings = get_settings()
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "docs": "/docs",
    }
