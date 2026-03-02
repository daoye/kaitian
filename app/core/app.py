"""FastAPI application factory for KaiTian."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.api import routes

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    # Startup
    logger.info("KaiTian application starting up")
    setup_logging()
    settings = get_settings()
    logger.info(
        f"Environment: {settings.environment}, "
        f"Debug: {settings.debug}, "
        f"Version: {settings.app_version}"
    )

    # Initialize data directories
    from app.services.state_store import (
        SESSIONS_DIR,
        CHECKPOINTS_DIR,
        FAILED_DIR,
        PLATFORM_SESSIONS_DIR,
    )

    for directory in [SESSIONS_DIR, CHECKPOINTS_DIR, FAILED_DIR, PLATFORM_SESSIONS_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
    logger.info("Data directories initialized")

    yield

    # Shutdown
    logger.info("KaiTian application shutting down")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="AI-powered product marketing automation MVP system",
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(routes.router)

    return app
