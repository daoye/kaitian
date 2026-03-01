"""API routes for KaiTian application.

All endpoints are designed to be called by n8n workflow.
n8n handles the orchestration and flow control.
KaiTian provides specialized capabilities:
  - Web crawling (Crawl4AI + MediaCrawler)
  - Social media posting (via Postiz)
  - Data storage and retrieval
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from datetime import datetime
from sqlalchemy.orm import Session
from typing import Optional, List
import json

from app.models.schemas import (
    HealthCheckResponse,
    RelevanceCheckRequest,
    RelevanceCheckResponse,
    ReplyGenerationRequest,
    ReplyGenerationResponse,
    PublishRequest,
    PublishResponse,
)
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.database import get_db
from app.integrations.crawl4ai_client import get_crawl4ai_client
from app.integrations.media_crawler_client import get_media_crawler_client
from app.integrations.postiz_client import get_postiz_client
from app.services.database_service import (
    create_post,
    update_post_status,
    get_posts_by_status,
    get_post_by_source_id,
    create_search_session,
    complete_search_session,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1", tags=["api"])


# ============================================================================
# 健康检查和信息端点
# ============================================================================


@router.get("/health", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    """Health check endpoint for n8n."""
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
        "description": "API service for n8n - provides crawling and posting capabilities",
        "docs": "/docs",
        "endpoints": {
            "crawling": ["/api/v1/crawl/url", "/api/v1/crawl/reddit"],
            "posting": ["/api/v1/post/reddit", "/api/v1/post/twitter"],
            "data": ["/api/v1/posts", "/api/v1/posts/{id}"],
        },
    }


# ============================================================================
# 爬虫 API 端点 - Crawl4AI
# ============================================================================


@router.post("/crawl/url")
async def crawl_url(url: str, wait_for: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Crawl a single URL using Crawl4AI.

    Called by n8n to extract content from any URL.

    Args:
        url: Target URL to crawl
        wait_for: CSS selector to wait for before extraction (optional)

    Returns:
        {
            "success": bool,
            "url": str,
            "content": str (markdown),
            "raw_html": str,
            "extracted_data": dict,
            "status_code": int,
            "error": str (if failed)
        }
    """
    try:
        logger.info(f"n8n crawl_url request: {url}")
        client = get_crawl4ai_client()

        result = await client.crawl(url=url, wait_for_selector=wait_for)

        return result

    except Exception as e:
        logger.error(f"Crawl URL failed: {str(e)}")
        return {"success": False, "url": url, "error": str(e)}


@router.post("/crawl/reddit")
async def crawl_reddit(
    subreddit: str,
    limit: int = Query(10, ge=1, le=100),
    keywords: Optional[List[str]] = None,
    db: Session = Depends(get_db),
):
    """
    Crawl Reddit subreddit posts using MediaCrawler.

    Called by n8n to fetch Reddit posts and store them in database.

    Args:
        subreddit: Subreddit name (e.g., "python")
        limit: Number of posts to fetch (1-100)
        keywords: Keywords to match against posts (optional)

    Returns:
        {
            "success": bool,
            "platform": "reddit",
            "subreddit": str,
            "posts": [
                {
                    "id": str,
                    "source_id": str,
                    "title": str,
                    "content": str,
                    "author": str,
                    "url": str,
                    "matched_keywords": [str],
                    "status": "pending"
                }
            ],
            "total_posts": int,
            "stored_posts": int,
            "error": str (if failed)
        }
    """
    try:
        logger.info(f"n8n crawl_reddit request: r/{subreddit}, limit={limit}")

        # Create search session
        search_keywords = keywords or get_settings().keywords
        session = create_search_session(db, search_keywords, "reddit")

        # Crawl Reddit
        client = get_media_crawler_client()
        result = client.crawl_reddit(subreddit=subreddit, limit=limit)

        if not result.get("success"):
            complete_search_session(db, session.id, error_message=result.get("error"))
            return result

        # Store posts in database
        posts = result.get("posts", [])
        stored_count = 0

        for post_data in posts:
            try:
                # Check if post already exists
                existing = get_post_by_source_id(db, post_data.get("id"))
                if existing:
                    continue

                # Match keywords
                matched = []
                content = f"{post_data.get('title', '')} {post_data.get('content', '')}".lower()
                for keyword in search_keywords:
                    if keyword.lower() in content:
                        matched.append(keyword)

                # Create post
                post = create_post(
                    db=db,
                    source_id=post_data.get("id"),
                    title=post_data.get("title"),
                    author=post_data.get("author"),
                    source_url=post_data.get("url"),
                    content=post_data.get("content"),
                    source_platform="reddit",
                )

                # Update with matched keywords
                update_post_status(
                    db=db,
                    post_id=post.id,
                    status="fetched",
                    matched_keywords=json.dumps(matched),
                    fetched_at=datetime.utcnow(),
                )

                stored_count += 1
            except Exception as e:
                logger.warning(f"Failed to store post {post_data.get('id')}: {str(e)}")
                continue

        # Complete search session
        complete_search_session(db, session.id, total_posts=len(posts), relevant_posts=stored_count)

        return {
            "success": True,
            "platform": "reddit",
            "subreddit": subreddit,
            "total_posts": len(posts),
            "stored_posts": stored_count,
            "posts": posts[:stored_count],  # Return stored posts
        }

    except Exception as e:
        logger.error(f"Crawl Reddit failed: {str(e)}")
        return {"success": False, "error": str(e)}


# ============================================================================
# 发帖 API 端点 - 社交媒体发布
# ============================================================================


@router.post("/post/reddit")
async def post_reddit(
    post_id: str,
    reply_text: str,
    reddit_integration_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Post a reply to a Reddit thread using Postiz.

    Called by n8n after human review to publish the reply.

    Args:
        post_id: KaiTian post ID
        reply_text: The reply text to post
        reddit_integration_id: Postiz Reddit integration ID (optional, from settings if not provided)

    Returns:
        {
            "success": bool,
            "post_id": str,
            "platform": "reddit",
            "published": bool,
            "published_id": str (if successful),
            "published_at": datetime,
            "postiz_post_id": str (Postiz post ID),
            "error": str (if failed)
        }
    """
    try:
        logger.info(f"n8n post_reddit request: post_id={post_id}")

        # Get post from database
        from app.models.db import Post

        post = db.query(Post).filter(Post.id == post_id).first()

        if not post:
            raise HTTPException(status_code=404, detail="Post not found")

        # Get Reddit integration ID
        settings = get_settings()
        integration_id = reddit_integration_id or settings.postiz_reddit_integration_id

        if not integration_id:
            logger.error("Reddit integration ID not configured")
            return {
                "success": False,
                "post_id": post_id,
                "platform": "reddit",
                "error": "Reddit integration ID not configured",
            }

        # Call Postiz API to publish
        postiz_client = get_postiz_client()

        result = await postiz_client.post_to_reddit(
            integration_id=integration_id,
            content=reply_text,
            subreddit=post.source_platform if post.source_platform == "reddit" else "AskReddit",
            title=f"Re: {post.title[:50]}...",  # Create a title from original
            post_type="self",
        )

        if result.get("success"):
            # Update post status
            update_post_status(
                db=db,
                post_id=post_id,
                status="published",
                published_id=result.get("post_id"),
                published_at=datetime.utcnow(),
            )

            logger.info(f"Successfully published to Reddit: {result.get('post_id')}")

            return {
                "success": True,
                "post_id": post_id,
                "platform": "reddit",
                "published": True,
                "published_id": result.get("post_id"),
                "postiz_post_id": result.get("post_id"),
                "published_at": datetime.utcnow(),
            }
        else:
            # Update with error
            update_post_status(
                db=db,
                post_id=post_id,
                status="failed",
                error_message=result.get("error"),
            )

            logger.error(f"Failed to publish to Reddit: {result.get('error')}")

            return {
                "success": False,
                "post_id": post_id,
                "platform": "reddit",
                "published": False,
                "error": result.get("error"),
            }

    except Exception as e:
        logger.error(f"Post Reddit failed: {str(e)}")
        return {"success": False, "error": str(e)}


@router.post("/post/twitter")
async def post_twitter(
    post_id: str,
    reply_text: str,
    twitter_integration_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Post a tweet/reply to Twitter using Postiz.

    Called by n8n after human review to publish.

    Args:
        post_id: KaiTian post ID
        reply_text: The tweet/reply text
        twitter_integration_id: Postiz Twitter integration ID (optional, from settings if not provided)

    Returns:
        {
            "success": bool,
            "post_id": str,
            "platform": "twitter",
            "published": bool,
            "published_id": str (if successful),
            "published_at": datetime,
            "postiz_post_id": str (Postiz post ID),
            "error": str (if failed)
        }
    """
    try:
        logger.info(f"n8n post_twitter request: post_id={post_id}")

        # Get post from database
        from app.models.db import Post

        post = db.query(Post).filter(Post.id == post_id).first()

        if not post:
            raise HTTPException(status_code=404, detail="Post not found")

        # Get Twitter integration ID
        settings = get_settings()
        integration_id = twitter_integration_id or settings.postiz_twitter_integration_id

        if not integration_id:
            logger.error("Twitter integration ID not configured")
            return {
                "success": False,
                "post_id": post_id,
                "platform": "twitter",
                "error": "Twitter integration ID not configured",
            }

        # Call Postiz API to publish
        postiz_client = get_postiz_client()

        result = await postiz_client.post_to_twitter(
            integration_id=integration_id, content=reply_text, who_can_reply="everyone"
        )

        if result.get("success"):
            # Update post status
            update_post_status(
                db=db,
                post_id=post_id,
                status="published",
                published_id=result.get("post_id"),
                published_at=datetime.utcnow(),
            )

            logger.info(f"Successfully published to Twitter: {result.get('post_id')}")

            return {
                "success": True,
                "post_id": post_id,
                "platform": "twitter",
                "published": True,
                "published_id": result.get("post_id"),
                "postiz_post_id": result.get("post_id"),
                "published_at": datetime.utcnow(),
            }
        else:
            # Update with error
            update_post_status(
                db=db,
                post_id=post_id,
                status="failed",
                error_message=result.get("error"),
            )

            logger.error(f"Failed to publish to Twitter: {result.get('error')}")

            return {
                "success": False,
                "post_id": post_id,
                "platform": "twitter",
                "published": False,
                "error": result.get("error"),
            }

    except Exception as e:
        logger.error(f"Post Twitter failed: {str(e)}")
        return {"success": False, "error": str(e)}


# ============================================================================
# 数据管理 API 端点
# ============================================================================


@router.get("/posts")
async def list_posts(
    status: Optional[str] = None,
    platform: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """
    List posts from database.

    Called by n8n to retrieve posts for processing.

    Args:
        status: Filter by status (pending, fetched, analyzed, relevant, published)
        platform: Filter by source platform (reddit, twitter, linkedin)
        limit: Maximum number of posts to return

    Returns:
        {
            "success": bool,
            "total": int,
            "posts": [...]
        }
    """
    try:
        from app.models.db import Post

        query = db.query(Post)

        if status:
            query = query.filter(Post.status == status)
        if platform:
            query = query.filter(Post.source_platform == platform)

        posts = query.order_by(Post.created_at.desc()).limit(limit).all()

        return {
            "success": True,
            "total": len(posts),
            "posts": [
                {
                    "id": p.id,
                    "source_id": p.source_id,
                    "title": p.title,
                    "author": p.author,
                    "status": p.status,
                    "relevance_score": p.relevance_score,
                    "created_at": p.created_at,
                    "url": p.source_url,
                }
                for p in posts
            ],
        }

    except Exception as e:
        logger.error(f"List posts failed: {str(e)}")
        return {"success": False, "error": str(e)}


@router.get("/posts/{post_id}")
async def get_post(post_id: str, db: Session = Depends(get_db)):
    """
    Get a specific post by ID.

    Args:
        post_id: Post ID

    Returns:
        Post details with all metadata
    """
    try:
        from app.models.db import Post

        post = db.query(Post).filter(Post.id == post_id).first()

        if not post:
            raise HTTPException(status_code=404, detail="Post not found")

        return {
            "success": True,
            "post": {
                "id": post.id,
                "source_id": post.source_id,
                "source_platform": post.source_platform,
                "title": post.title,
                "content": post.content,
                "author": post.author,
                "url": post.source_url,
                "status": post.status,
                "relevance_score": post.relevance_score,
                "relevance_reason": post.relevance_reason,
                "matched_keywords": json.loads(post.matched_keywords)
                if post.matched_keywords
                else [],
                "generated_reply": post.generated_reply,
                "reply_confidence": post.reply_confidence,
                "created_at": post.created_at,
                "updated_at": post.updated_at,
                "published_at": post.published_at,
            },
        }

    except Exception as e:
        logger.error(f"Get post failed: {str(e)}")
        return {"success": False, "error": str(e)}


@router.patch("/posts/{post_id}")
async def update_post(
    post_id: str,
    status: Optional[str] = None,
    relevance_score: Optional[float] = None,
    generated_reply: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Update post status and metadata.

    Called by n8n to track processing progress.

    Args:
        post_id: Post ID
        status: New status
        relevance_score: Relevance score (0-1)
        generated_reply: Generated reply text

    Returns:
        Updated post data
    """
    try:
        from app.models.db import Post

        post = db.query(Post).filter(Post.id == post_id).first()

        if not post:
            raise HTTPException(status_code=404, detail="Post not found")

        kwargs = {}
        if status:
            kwargs["status"] = status
        if relevance_score is not None:
            kwargs["relevance_score"] = relevance_score
        if generated_reply:
            kwargs["generated_reply"] = generated_reply

        updated = update_post_status(db, post_id, status or post.status, **kwargs)

        return {
            "success": True,
            "post_id": post_id,
            "status": updated.status if updated else post.status,
        }

    except Exception as e:
        logger.error(f"Update post failed: {str(e)}")
        return {"success": False, "error": str(e)}
