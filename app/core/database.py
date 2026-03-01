"""Database configuration and session management for KaiTian."""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def get_db_engine():
    """Create and return database engine."""
    settings = get_settings()

    # SQLite specific configuration
    if settings.database_url.startswith("sqlite://"):
        engine = create_engine(
            settings.database_url,
            echo=settings.database_echo,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        # Enable foreign keys for SQLite
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    else:
        engine = create_engine(
            settings.database_url,
            echo=settings.database_echo,
        )

    logger.info(f"Database engine created: {settings.database_url}")
    return engine


def get_session_factory():
    """Create and return session factory."""
    engine = get_db_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """Get database session for dependency injection."""
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database, create all tables."""
    from app.models.db import Base

    engine = get_db_engine()
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")
