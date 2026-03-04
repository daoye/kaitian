"""Data models for KaiTian application."""

from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
from typing import Optional
from typing import List, Dict, Any


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


class HealthCheckResponse(BaseModel):
    """Response model for health check."""

    status: str
    version: str
    timestamp: datetime


class KeywordUniverseCreate(BaseModel):
    name: str
    description: Optional[str] = None
    keywords: List[str]
    category: Optional[str] = None
    tags: Optional[List[str]] = None


class KeywordUniverseResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    keywords: List[str]
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


class SocialSearchRequest(BaseModel):
    keyword: str
    platforms: List[str]
    limit_per_page: Optional[int] = 10
    pages: Optional[int] = 3
    filters: Optional[Dict[str, Any]] = None


class SocialSearchResponse(BaseModel):
    success: bool
    search_id: Optional[str] = None
    keyword: Optional[str] = None
    total_results: Optional[int] = 0
    results_per_platform: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class NotificationPushRequest(BaseModel):
    reply_id: str
    post_id: str
    original_content: str
    generated_reply: str
    callback_url: str
    metadata: Optional[Dict[str, Any]] = None
    expires_in_hours: Optional[int] = 24


class NotificationPushResponse(BaseModel):
    success: bool
    notification_id: Optional[str] = None
    lihuo_message_id: Optional[str] = None
    status: Optional[str] = None
    expires_at: Optional[datetime] = None
    error: Optional[str] = None


class ReviewCallbackRequest(BaseModel):
    notification_id: str
    action: str  # approved or rejected
    user_notes: Optional[str] = None


class ReviewCallbackResponse(BaseModel):
    success: bool
    notification_id: Optional[str] = None
    action: Optional[str] = None


# ============================================================================
# Post Detail Models - 帖子详情爬取
# ============================================================================


class PlatformEnum(str, Enum):
    """支持的社交媒体平台"""

    REDDIT = "reddit"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    XHS = "xhs"  # 小红书
    DY = "dy"  # 抖音
    BILI = "bili"  # B站
    ZHIHU = "zhihu"  # 知乎


class PostDetailRequest(BaseModel):
    """帖子详情爬取请求"""

    url: str = Field(..., description="帖子 URL")
    platform: PlatformEnum = Field(..., description="平台类型")
    extract_comments: bool = Field(default=False, description="是否提取评论")
    max_comments: int = Field(default=10, description="最大评论数")


class PostEngagement(BaseModel):
    """帖子互动数据"""

    upvotes: Optional[int] = Field(default=None, description="点赞数")
    downvotes: Optional[int] = Field(default=None, description="踩数")
    comments_count: Optional[int] = Field(default=None, description="评论数")
    shares: Optional[int] = Field(default=None, description="分享数")
    views: Optional[int] = Field(default=None, description="浏览数")
    likes: Optional[int] = Field(default=None, description="喜欢数")
    retweets: Optional[int] = Field(default=None, description="转发数")


class PostComment(BaseModel):
    """帖子评论"""

    comment_id: str = Field(..., description="评论 ID")
    author: str = Field(..., description="评论者")
    content: str = Field(..., description="评论内容")
    created_at: Optional[str] = Field(default=None, description="评论时间")
    upvotes: Optional[int] = Field(default=None, description="点赞数")


class PostDetail(BaseModel):
    """帖子详情"""

    post_id: str = Field(..., description="帖子 ID")
    platform: str = Field(..., description="平台")
    url: str = Field(..., description="帖子 URL")
    title: Optional[str] = Field(default=None, description="标题")
    content: str = Field(..., description="正文内容")
    author: str = Field(..., description="作者")
    author_id: Optional[str] = Field(default=None, description="作者 ID")
    author_url: Optional[str] = Field(default=None, description="作者主页 URL")
    created_at: Optional[str] = Field(default=None, description="发布时间")
    engagement: PostEngagement = Field(default_factory=PostEngagement, description="互动数据")
    comments: List[PostComment] = Field(default_factory=list, description="评论列表")
    media_urls: List[str] = Field(default_factory=list, description="媒体 URL（图片/视频）")
    tags: List[str] = Field(default_factory=list, description="标签")
    subreddit: Optional[str] = Field(default=None, description="Subreddit（Reddit专用）")


class PostDetailResponse(BaseModel):
    """帖子详情爬取响应"""

    success: bool = Field(..., description="是否成功")
    post: Optional[PostDetail] = Field(default=None, description="帖子详情")
    raw_content: Optional[str] = Field(default=None, description="原始 Markdown 内容")
    error: Optional[str] = Field(default=None, description="错误信息")


# ============================================================================
# Publisher Models - 发布能力
# ============================================================================


class PublishPlatformEnum(str, Enum):
    """支持发布的平台"""

    REDDIT = "reddit"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    XIAOHONGSHU = "xiaohongshu"
    TIEBA = "tieba"


class PublishPostRequest(BaseModel):
    """发布帖子请求"""

    platform: PublishPlatformEnum = Field(..., description="目标平台")
    title: Optional[str] = Field(default=None, description="标题（Reddit/Tieba必需）")
    content: str = Field(..., description="帖子内容")
    subreddit: Optional[str] = Field(default=None, description="Subreddit名称（Reddit专用）")
    media_urls: Optional[List[str]] = Field(default=None, description="媒体URL列表")
    images: Optional[List[str]] = Field(
        default=None, description="图片路径列表（Xiaohongshu必需,Tieba可选）"
    )
    location: Optional[str] = Field(default=None, description="地点标签（Xiaohongshu可选）")
    forum_name: Optional[str] = Field(default=None, description="贴吧名称（Tieba必需）")


class PublishPostResponse(BaseModel):
    """发布帖子响应"""

    success: bool = Field(..., description="是否成功")
    post_id: Optional[str] = Field(default=None, description="发布的帖子ID")
    post_url: Optional[str] = Field(default=None, description="帖子URL")
    platform: Optional[str] = Field(default=None, description="平台")
    error: Optional[str] = Field(default=None, description="错误信息")


class PublishCommentRequest(BaseModel):
    """发布评论请求"""

    platform: PublishPlatformEnum = Field(..., description="目标平台")
    post_url: str = Field(..., description="目标帖子URL")
    content: str = Field(..., description="评论内容")
    parent_comment_id: Optional[str] = Field(default=None, description="父评论ID（用于回复评论）")


class PublishCommentResponse(BaseModel):
    """发布评论响应"""

    success: bool = Field(..., description="是否成功")
    comment_id: Optional[str] = Field(default=None, description="评论ID")
    comment_url: Optional[str] = Field(default=None, description="评论URL")
    platform: Optional[str] = Field(default=None, description="平台")
    error: Optional[str] = Field(default=None, description="错误信息")
