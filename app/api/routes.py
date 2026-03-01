"""API routes for KaiTian application.

KaiTian is a data persistence and web scraping service for n8n workflows.
All endpoints support n8n's HTTP Request node.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from datetime import datetime
from sqlalchemy.orm import Session
from typing import Optional, List
import json

from app.models.schemas import HealthCheckResponse
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.database import get_db
from app.integrations.crawl4ai_client import get_crawl4ai_client
from app.services.database_service import (
    create_post,
    update_post_status,
    get_posts_by_status,
    get_post_by_source_id,
    create_search_session,
    complete_search_session,
)
from app.services.content_generation import (
    ArticleGenerationRequest,
    ArticleGenerationResponse,
    SEOOptimizationRequest,
    SEOOptimizationResponse,
    get_content_generation_service,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1", tags=["api"])


# ============================================================================
# Health Check and Info Endpoints
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
    """Root API endpoint with service information."""
    settings = get_settings()
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "description": "Web scraping and data persistence service for n8n workflows",
        "docs": "/docs",
        "endpoints": {
            "crawling": ["/api/v1/crawl/url"],
            "data": ["/api/v1/posts", "/api/v1/posts/{id}"],
        },
    }


# ============================================================================
# Web Crawling Endpoints
# ============================================================================


@router.post("/crawl/url")
async def crawl_url(
    url: str,
    wait_for: Optional[str] = None,
    store_to_db: Optional[bool] = False,
    db: Session = Depends(get_db),
):
    """
    Crawl a single URL using Crawl4AI.

    Called by n8n to extract content from any URL.

    Args:
        url: Target URL to crawl
        wait_for: CSS selector to wait for before extraction (optional)
        store_to_db: Store crawled content as post in database (optional)

    Returns:
        {
            "success": bool,
            "url": str,
            "content": str (markdown),
            "raw_html": str,
            "extracted_data": dict,
            "status_code": int,
            "post_id": str (if stored_to_db),
            "error": str (if failed)
        }
    """
    try:
        logger.info(f"Crawling URL: {url}")
        client = get_crawl4ai_client()

        result = await client.crawl(url=url, wait_for_selector=wait_for)

        # Optionally store result in database
        if store_to_db and result.get("success"):
            try:
                post = create_post(
                    db=db,
                    source_id=url,
                    title=f"Crawled: {url[:100]}",
                    author="n8n",
                    source_url=url,
                    content=result.get("content"),
                    source_platform="web",
                )
                result["post_id"] = post.id
                logger.info(f"Stored crawled content as post: {post.id}")
            except Exception as e:
                logger.warning(f"Failed to store crawled content: {str(e)}")

        return result

    except Exception as e:
        logger.error(f"Crawl URL failed: {str(e)}")
        return {"success": False, "url": url, "error": str(e)}


# ============================================================================
# Data Management Endpoints
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
        platform: Filter by source platform (reddit, twitter, web, etc.)
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
                    "platform": p.source_platform,
                    "status": p.status,
                    "relevance_score": p.relevance_score,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
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
                "matched_keywords": (
                    json.loads(post.matched_keywords) if post.matched_keywords else []
                ),
                "generated_reply": post.generated_reply,
                "reply_confidence": post.reply_confidence,
                "created_at": post.created_at.isoformat() if post.created_at else None,
                "updated_at": post.updated_at.isoformat() if post.updated_at else None,
                "published_at": post.published_at.isoformat() if post.published_at else None,
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
    relevance_reason: Optional[str] = None,
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
        relevance_reason: Reason for relevance decision

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
        if relevance_reason:
            kwargs["relevance_reason"] = relevance_reason

        updated = update_post_status(db, post_id, status or post.status, **kwargs)

        return {
            "success": True,
            "post_id": post_id,
            "status": updated.status if updated else post.status,
        }

    except Exception as e:
        logger.error(f"Update post failed: {str(e)}")
        return {"success": False, "error": str(e)}


@router.delete("/posts/{post_id}")
async def delete_post(post_id: str, db: Session = Depends(get_db)):
    """
    Delete a post from database.

    Args:
        post_id: Post ID

    Returns:
        Deletion confirmation
    """
    try:
        from app.models.db import Post

        post = db.query(Post).filter(Post.id == post_id).first()

        if not post:
            raise HTTPException(status_code=404, detail="Post not found")

        db.delete(post)
        db.commit()
        logger.info(f"Deleted post: {post_id}")

        return {
            "success": True,
            "message": f"Post {post_id} deleted successfully",
        }

    except Exception as e:
        logger.error(f"Delete post failed: {str(e)}")
        return {"success": False, "error": str(e)}


# ============================================================================
# 内容生成端点 (LangChain 集成)
# ============================================================================


@router.post("/generate/article", response_model=ArticleGenerationResponse)
async def generate_article(request: ArticleGenerationRequest) -> ArticleGenerationResponse:
    """生成营销文章。

    使用 LangChain 和 LLM 生成高质量的营销文章。

    Args:
        request: 文章生成请求

    Returns:
        文章生成响应

    Example:
        ```bash
        POST /api/v1/generate/article
        {
            "topic": "AI 在营销中的应用",
            "keywords": ["AI", "营销", "自动化"],
            "tone": "professional",
            "length": "medium",
            "language": "zh",
            "target_audience": "营销团队"
        }
        ```
    """
    try:
        service = get_content_generation_service()
        result = await service.generate_article(request)

        logger.info(
            f"文章生成完成: {request.topic} "
            f"(字数: {result.content.word_count if result.content else 0}, "
            f"耗时: {result.metadata.get('generation_time', 0)}s)"
        )

        return result

    except Exception as e:
        logger.error(f"文章生成请求处理失败: {str(e)}")
        return ArticleGenerationResponse(
            success=False, error=f"服务器错误: {str(e)}", error_code="SERVER_ERROR"
        )


@router.post("/generate/articles/batch")
async def generate_articles_batch(requests: List[ArticleGenerationRequest]):
    """批量生成文章。

    同时生成多篇文章。

    Args:
        requests: 文章生成请求列表

    Returns:
        文章生成结果列表
    """
    try:
        service = get_content_generation_service()
        results = []

        for request in requests:
            result = await service.generate_article(request)
            results.append(result)
            logger.info(f"批量生成进度: {len(results)}/{len(requests)}")

        return {
            "success": True,
            "total": len(requests),
            "completed": len([r for r in results if r.success]),
            "articles": results,
        }

    except Exception as e:
        logger.error(f"批量文章生成失败: {str(e)}")
        return {"success": False, "error": str(e)}


@router.post("/generate/optimize", response_model=SEOOptimizationResponse)
async def optimize_content(request: SEOOptimizationRequest) -> SEOOptimizationResponse:
    """优化文章的 SEO 表现。

    分析并优化现有文章的搜索引擎优化。

    Args:
        request: SEO 优化请求

    Returns:
        SEO 优化响应

    Example:
        ```bash
        POST /api/v1/generate/optimize
        {
            "article": "文章内容...",
            "keywords": ["关键词1", "关键词2"],
            "language": "zh",
            "target_audience": "一般用户"
        }
        ```
    """
    try:
        service = get_content_generation_service()
        result = await service.optimize_seo(request)

        if result.success:
            logger.info(f"SEO 优化完成: SEO 评分: {result.seo_score}/100")

        return result

    except Exception as e:
        logger.error(f"SEO 优化请求处理失败: {str(e)}")
        return SEOOptimizationResponse(success=False, error=f"服务器错误: {str(e)}")


@router.get("/generate/status")
async def get_generation_status():
    """获取内容生成服务状态。

    Returns:
        服务状态信息
    """
    try:
        settings = get_settings()
        service = get_content_generation_service()

        return {
            "success": True,
            "service": "content_generation",
            "status": "operational",
            "llm_provider": settings.llm_provider,
            "model": settings.openai_model if settings.llm_provider == "openai" else "unknown",
            "cache_enabled": settings.content_generation_cache_enabled,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"获取服务状态失败: {str(e)}")
        return {"success": False, "status": "error", "error": str(e)}
