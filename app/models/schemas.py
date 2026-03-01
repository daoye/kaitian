"""Data models for KaiTian application."""

from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
from typing import Optional


class PostStatusEnum(str, Enum):
    """Enumeration for post processing status."""

    PENDING = "pending"
    RELEVANT = "relevant"
    IRRELEVANT = "irrelevant"
    REPLY_GENERATED = "reply_generated"
    REPLY_APPROVED = "reply_approved"
    PUBLISHED = "published"
    FAILED = "failed"


class SourcePlatformEnum(str, Enum):
    """Enumeration for source platforms."""

    REDDIT = "reddit"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    HACKERNEWS = "hackernews"


class PublishPlatformEnum(str, Enum):
    """Enumeration for target publish platforms."""

    REDDIT = "reddit"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"


class RedditPostBase(BaseModel):
    """Base model for Reddit posts."""

    post_id: str
    title: str
    content: Optional[str] = None
    author: str
    subreddit: str
    url: str
    created_at: datetime


class RedditPost(RedditPostBase):
    """Model for stored Reddit posts with metadata."""

    status: PostStatusEnum = PostStatusEnum.PENDING
    relevance_score: Optional[float] = None
    relevance_reason: Optional[str] = None
    matched_keywords: list[str] = Field(default_factory=list)
    generated_reply: Optional[str] = None
    reply_confidence: Optional[float] = None
    manual_review_status: Optional[bool] = None
    manual_review_feedback: Optional[str] = None
    published_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at_db: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class RelevanceCheckRequest(BaseModel):
    """Request model for relevance checking."""

    post_id: str
    title: str
    content: Optional[str] = None
    keywords: list[str]


class RelevanceCheckResponse(BaseModel):
    """Response model for relevance checking."""

    post_id: str
    is_relevant: bool
    relevance_score: float
    reason: str


class ReplyGenerationRequest(BaseModel):
    """Request model for reply generation."""

    post_id: str
    title: str
    content: Optional[str] = None
    author: str
    subreddit: str
    context: Optional[str] = None


class ReplyGenerationResponse(BaseModel):
    """Response model for reply generation."""

    post_id: str
    reply_text: str
    confidence: float


class PublishRequest(BaseModel):
    """Request model for publishing replies."""

    post_id: str
    platform: PublishPlatformEnum
    reply_text: str
    target_url: str
    metadata: Optional[dict] = None


class PublishResponse(BaseModel):
    """Response model for publishing."""

    post_id: str
    platform: PublishPlatformEnum
    success: bool
    published_id: Optional[str] = None
    error_message: Optional[str] = None
    published_at: datetime


class HealthCheckResponse(BaseModel):
    """Response model for health check."""

    status: str
    version: str
    timestamp: datetime
