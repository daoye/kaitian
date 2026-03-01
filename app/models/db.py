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


# ============================================================================
# 新工作流相关的数据模型
# ============================================================================


class KeywordUniverse(Base):
    """关键词宇宙 - 用户定义的关键词集合。"""

    __tablename__ = "keyword_universes"

    id = Column(String(255), primary_key=True)
    name = Column(String(500), nullable=False, index=True)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)
    tags = Column(Text, nullable=True)  # JSON array
    keywords = Column(Text, nullable=False)  # JSON array

    # Metadata
    is_active = Column(Boolean, default=True, index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    search_sessions = relationship("SearchSession", back_populates="universe")


class SocialMediaPost(Base):
    """社交媒体帖子 - 从社交媒体平台爬取的内容。"""

    __tablename__ = "social_media_posts"

    id = Column(String(255), primary_key=True)
    post_id = Column(String(500), nullable=False, unique=True, index=True)
    platform = Column(String(50), nullable=False, index=True)  # reddit, twitter, linkedin
    title = Column(String(1000), nullable=True)
    content = Column(Text, nullable=False)
    author = Column(String(255), nullable=True)
    author_id = Column(String(255), nullable=True)
    url = Column(String(1000), nullable=False)

    # Engagement metrics
    engagement = Column(Text, nullable=True)  # JSON: {upvotes, comments, shares, etc}

    # AI evaluation
    relevance_score = Column(Float, nullable=True)
    is_relevant = Column(Boolean, nullable=True)
    relevance_reasoning = Column(Text, nullable=True)
    suggested_angle = Column(Text, nullable=True)

    # Sentiment and intent analysis
    sentiment = Column(String(50), nullable=True)  # positive, neutral, negative
    intent = Column(String(100), nullable=True)  # product_evaluation, question, complaint, etc
    urgency = Column(String(50), nullable=True)  # low, medium, high

    # Original post metadata
    created_at_original = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    evaluated_at = Column(DateTime, nullable=True)

    # Relationships
    generated_reply = relationship("GeneratedReply", back_populates="social_post", uselist=False)


class GeneratedReply(Base):
    """生成的回复 - AI 生成的针对性回复。"""

    __tablename__ = "generated_replies"

    id = Column(String(255), primary_key=True)
    post_id = Column(String(255), ForeignKey("social_media_posts.id"), nullable=False)

    # Reply content
    original_reply = Column(Text, nullable=False)  # AI 初始生成的回复
    current_reply = Column(Text, nullable=False)  # 用户可能编辑过的回复
    reply_alternatives = Column(Text, nullable=True)  # JSON array of alternatives

    # Quality metrics
    confidence = Column(Float, nullable=True)
    word_count = Column(Integer, nullable=True)
    tone_match_score = Column(Float, nullable=True)

    # Status
    status = Column(
        String(50), default="pending", index=True
    )  # pending, approved, rejected, published
    review_status = Column(String(50), nullable=True)  # pending_review, approved, rejected
    user_notes = Column(Text, nullable=True)  # 用户在审核时添加的备注

    # Publishing
    published_url = Column(String(1000), nullable=True)
    published_at = Column(DateTime, nullable=True)
    publish_error = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)

    # Relationships
    social_post = relationship("SocialMediaPost", back_populates="generated_reply")
    review_notification = relationship("ReviewNotification", back_populates="reply", uselist=False)


class ReviewNotification(Base):
    """审核通知 - 推送到 LihuApp 的审核通知。"""

    __tablename__ = "review_notifications"

    id = Column(String(255), primary_key=True)
    reply_id = Column(String(255), ForeignKey("generated_replies.id"), nullable=False)

    # LihuApp integration
    lihuo_message_id = Column(String(500), nullable=True)
    lihuo_push_status = Column(String(50), nullable=True)  # sent, delivered, failed

    # Status
    status = Column(
        String(50), default="pending", index=True
    )  # sent, acknowledged, approved, rejected, expired, timeout
    result = Column(String(50), nullable=True)  # approved, rejected

    # Callback
    callback_url = Column(String(1000), nullable=False)
    callback_received = Column(Boolean, default=False)
    callback_received_at = Column(DateTime, nullable=True)

    # Expiration
    expires_at = Column(DateTime, nullable=False)

    # User feedback
    user_notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    sent_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    reply = relationship("GeneratedReply", back_populates="review_notification")


class SearchSession(Base):
    """Search session model for tracking search operations."""

    __tablename__ = "search_sessions"

    id = Column(String(255), primary_key=True)
    universe_id = Column(String(255), ForeignKey("keyword_universes.id"), nullable=True)
    keyword = Column(String(500), nullable=False, index=True)
    platforms = Column(Text, nullable=False)  # JSON array
    pages = Column(Integer, default=3)

    # Results
    total_results = Column(Integer, default=0)
    relevant_count = Column(Integer, default=0)

    # Status
    status = Column(String(50), default="pending", index=True)  # in_progress, completed, failed
    error_message = Column(Text, nullable=True)

    # Duration
    duration_seconds = Column(Float, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    universe = relationship("KeywordUniverse", back_populates="search_sessions")
