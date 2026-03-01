"""Database initialization and utility functions."""

import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.db import (
    Post,
    SearchSession,
    CrawlSession,
    ProcessingLog,
    PostStatusEnum,
    SourcePlatformEnum,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


def init_database(db: Session):
    """Initialize database with schema."""
    from app.core.database import get_db_engine
    from app.models.db import Base

    engine = get_db_engine()
    logger.info("Initializing database schema...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema initialized successfully")


def create_post(
    db: Session,
    source_id: str,
    title: str,
    author: str,
    source_url: str,
    content: str = None,
    source_platform: str = SourcePlatformEnum.REDDIT,
) -> Post:
    """Create a new post record."""
    post = Post(
        id=str(uuid.uuid4()),
        source_platform=source_platform,
        source_id=source_id,
        title=title,
        content=content,
        author=author,
        source_url=source_url,
        status=PostStatusEnum.PENDING,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    logger.info(f"Created post: {post.id}")
    return post


def update_post_status(db: Session, post_id: str, status: str, **kwargs) -> Post:
    """Update post status and optional fields."""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        logger.error(f"Post not found: {post_id}")
        return None

    post.status = status
    post.updated_at = datetime.utcnow()

    for key, value in kwargs.items():
        if hasattr(post, key):
            setattr(post, key, value)

    db.commit()
    db.refresh(post)
    logger.info(f"Updated post {post_id} status to {status}")
    return post


def create_search_session(
    db: Session, keywords: list[str], source_platform: str = SourcePlatformEnum.REDDIT
) -> SearchSession:
    """Create a new search session."""
    import json

    session = SearchSession(
        id=str(uuid.uuid4()),
        source_platform=source_platform,
        keywords=json.dumps(keywords),
        status="started",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    logger.info(f"Created search session: {session.id}")
    return session


def complete_search_session(
    db: Session,
    session_id: str,
    total_posts: int = 0,
    relevant_posts: int = 0,
    error_message: str = None,
) -> SearchSession:
    """Mark search session as completed."""
    session = db.query(SearchSession).filter(SearchSession.id == session_id).first()
    if not session:
        logger.error(f"Search session not found: {session_id}")
        return None

    session.completed_at = datetime.utcnow()
    session.total_posts_found = total_posts
    session.relevant_posts = relevant_posts
    session.status = "failed" if error_message else "completed"
    session.error_message = error_message

    if session.created_at:
        duration = (session.completed_at - session.created_at).total_seconds()
        session.duration_seconds = duration

    db.commit()
    db.refresh(session)
    logger.info(f"Completed search session {session_id}")
    return session


def create_crawl_session(db: Session, crawler_type: str, target_url: str) -> CrawlSession:
    """Create a new crawl session."""
    session = CrawlSession(
        id=str(uuid.uuid4()),
        crawler_type=crawler_type,
        target_url=target_url,
        status="pending",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    logger.info(f"Created crawl session: {session.id} ({crawler_type})")
    return session


def complete_crawl_session(
    db: Session,
    session_id: str,
    page_content: str = None,
    extracted_data: str = None,
    status_code: int = None,
    error_message: str = None,
) -> CrawlSession:
    """Mark crawl session as completed."""
    session = db.query(CrawlSession).filter(CrawlSession.id == session_id).first()
    if not session:
        logger.error(f"Crawl session not found: {session_id}")
        return None

    session.completed_at = datetime.utcnow()
    session.page_content = page_content
    session.extracted_data = extracted_data
    session.status_code = status_code
    session.status = "failed" if error_message else "completed"
    session.error_message = error_message

    if session.started_at:
        duration = (session.completed_at - session.started_at).total_seconds()
        session.duration_seconds = duration

    db.commit()
    db.refresh(session)
    logger.info(f"Completed crawl session {session_id}")
    return session


def log_operation(
    db: Session,
    operation: str,
    status: str,
    post_id: str = None,
    details: str = None,
    error_message: str = None,
    duration_ms: int = None,
) -> ProcessingLog:
    """Create a processing log entry."""
    log = ProcessingLog(
        id=str(uuid.uuid4()),
        post_id=post_id,
        operation=operation,
        status=status,
        details=details,
        error_message=error_message,
        duration_milliseconds=duration_ms,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def get_posts_by_status(db: Session, status: str, limit: int = 100) -> list[Post]:
    """Get posts by status."""
    return db.query(Post).filter(Post.status == status).limit(limit).all()


def get_post_by_source_id(db: Session, source_id: str) -> Post:
    """Get post by source ID."""
    return db.query(Post).filter(Post.source_id == source_id).first()
