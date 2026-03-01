"""SQLAlchemy ORM models for KaiTian database."""

from sqlalchemy import Column, String, Text, Integer, Float, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
from enum import Enum as PyEnum

Base = declarative_base()


class PostStatusEnum(str, PyEnum):
    """Post processing status enumeration."""

    PENDING = "pending"
    FETCHED = "fetched"
    ANALYZED = "analyzed"
    RELEVANT = "relevant"
    IRRELEVANT = "irrelevant"
    REPLY_GENERATED = "reply_generated"
    REPLY_APPROVED = "reply_approved"
    PUBLISHED = "published"
    FAILED = "failed"


class SourcePlatformEnum(str, PyEnum):
    """Source platform enumeration."""

    REDDIT = "reddit"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    CUSTOM = "custom"


class PublishPlatformEnum(str, PyEnum):
    """Publish platform enumeration."""

    REDDIT = "reddit"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"


class Post(Base):
    """Post model for storing social media posts."""

    __tablename__ = "posts"

    id = Column(String(255), primary_key=True)
    source_platform = Column(String(50), default=SourcePlatformEnum.REDDIT)
    source_id = Column(String(255), nullable=False, unique=True, index=True)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=True)
    author = Column(String(255), nullable=False)
    source_url = Column(String(1000), nullable=False)

    # Metadata
    status = Column(String(50), default=PostStatusEnum.PENDING, index=True)
    relevance_score = Column(Float, nullable=True)
    relevance_reason = Column(Text, nullable=True)
    matched_keywords = Column(String(500), nullable=True)  # JSON-serialized list

    # Reply information
    generated_reply = Column(Text, nullable=True)
    reply_confidence = Column(Float, nullable=True)
    manual_review = Column(Boolean, default=False)
    manual_review_feedback = Column(Text, nullable=True)

    # Publishing information
    published_at = Column(DateTime, nullable=True)
    published_platform = Column(String(50), nullable=True)
    published_id = Column(String(255), nullable=True)

    # Error tracking
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    fetched_at = Column(DateTime, nullable=True)
    analyzed_at = Column(DateTime, nullable=True)


class SearchSession(Base):
    """Search session model for tracking search operations."""

    __tablename__ = "search_sessions"

    id = Column(String(255), primary_key=True)
    source_platform = Column(String(50), default=SourcePlatformEnum.REDDIT)
    keywords = Column(String(1000), nullable=False)  # JSON-serialized list
    query_params = Column(Text, nullable=True)  # JSON-serialized dict

    # Results
    total_posts_found = Column(Integer, default=0)
    relevant_posts = Column(Integer, default=0)

    # Status
    status = Column(String(50), default="pending")
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)


class CrawlSession(Base):
    """Web crawl session model for tracking Crawl4AI and MediaCrawler operations."""

    __tablename__ = "crawl_sessions"

    id = Column(String(255), primary_key=True)
    crawler_type = Column(String(50), nullable=False)  # 'crawl4ai', 'media_crawler'
    target_url = Column(String(1000), nullable=False)

    # Crawl results
    page_content = Column(Text, nullable=True)
    extracted_data = Column(Text, nullable=True)  # JSON-serialized
    status_code = Column(Integer, nullable=True)

    # Metadata
    status = Column(String(50), default="pending")
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)


class ProcessingLog(Base):
    """Processing log for audit trail and debugging."""

    __tablename__ = "processing_logs"

    id = Column(String(255), primary_key=True)
    post_id = Column(String(255), ForeignKey("posts.id"), nullable=True)
    operation = Column(
        String(100), nullable=False
    )  # 'search', 'analyze', 'generate_reply', 'publish'
    status = Column(String(50), nullable=False)  # 'started', 'completed', 'failed'

    # Details
    details = Column(Text, nullable=True)  # JSON-serialized
    error_message = Column(Text, nullable=True)
    duration_milliseconds = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    post = relationship("Post", foreign_keys=[post_id])
