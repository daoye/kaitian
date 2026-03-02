"""API routes for KaiTian application.

KaiTian provides capabilities for n8n workflows.
All endpoints support n8n's HTTP Request node.

Capabilities:
- Web Crawling: crawl URLs and social media content
- AI Evaluation: evaluate content relevance
- AI Generation: generate replies and articles
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime
from typing import Optional, List

from app.models.schemas import HealthCheckResponse
from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.content_generation import (
    ArticleGenerationRequest,
    ArticleGenerationResponse,
    SEOOptimizationRequest,
    SEOOptimizationResponse,
    get_content_generation_service,
)
from app.services.social_media_crawler import social_media_crawler_service
from app.services.langchain_agent import langchain_agent_service
from app.models.schemas import (
    SocialSearchRequest,
    SocialSearchResponse,
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
        "description": "Web scraping and AI capabilities for n8n workflows",
        "docs": "/docs",
        "endpoints": {
            "crawler": ["/api/v1/crawler/url", "/api/v1/crawler/search"],
            "ai": [
                "/api/v1/ai/evaluate/relevance",
                "/api/v1/ai/generate/reply",
                "/api/v1/ai/generate/article",
                "/api/v1/ai/generate/optimize",
                "/api/v1/ai/status",
            ],
        },
    }


# ============================================================================
# Crawler Endpoints
# ============================================================================


@router.post("/crawler/url")
async def crawl_url(
    url: str,
    wait_for: Optional[str] = None,
):
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
        logger.info(f"Crawling URL: {url}")

        # 调用本地部署的 crawl4ai API
        crawl4ai_url = get_settings().crawl4ai_api_url or "http://localhost:8001"
        payload = {"urls": [url], "priority": 10}

        import requests

        response = requests.post(
            f"{crawl4ai_url}/crawl",
            json=payload,
            timeout=30,
        )

        result = {}
        if response.status_code == 200:
            data = response.json()
            if data.get("results"):
                result = {
                    "success": True,
                    "url": url,
                    "content": data["results"][0].get("markdown", ""),
                    "raw_html": data["results"][0].get("html", ""),
                    "extracted_data": {},
                    "status_code": 200,
                }
            elif data.get("task_id"):
                # 异步任务，简化处理返回错误
                result = {"success": False, "url": url, "error": "Async task not supported"}
        else:
            result = {"success": False, "url": url, "error": f"HTTP {response.status_code}"}

        return result

    except Exception as e:
        logger.error(f"Crawl URL failed: {str(e)}")
        return {"success": False, "url": url, "error": str(e)}


@router.post("/crawler/search")
async def search_social_media(
    keyword: str,
    platforms: Optional[List[str]] = None,
    max_results: int = 10,
):
    """
    搜索社交媒体内容。

    纯粹的能力提供 - n8n 负责关键词管理和结果处理。

    Args:
        keyword: 搜索关键词
        platforms: 目标平台列表 ["reddit", "twitter", "linkedin", "xhs", "dy", "bili", "zhihu"]
        max_results: 最大结果数

    Returns:
        帖子列表，包含标题、内容、作者、URL、互动数据等
    """
    try:
        service = social_media_crawler_service
        result = await service.crawl_with_crawl4ai(
            keyword=keyword,
            platforms=platforms,
            max_results=max_results,
        )
        return result
    except Exception as e:
        logger.error(f"Social media search failed: {str(e)}")
        return {"success": False, "error": str(e)}


@router.post("/crawler/get")
async def crawl_post_detail(
    url: str,
    platform: str = "reddit",
    extract_comments: bool = False,
    max_comments: int = 10,
):
    """
    爬取单个帖子的详细内容。

    n8n 在获取搜索结果后，调用此 API 获取每个帖子的完整内容。

    Args:
        url: 帖子 URL
        platform: 平台类型 (reddit, twitter, linkedin, xhs, dy, bili, zhihu)
        extract_comments: 是否提取评论（默认 False）
        max_comments: 最大评论数（默认 10）

    Returns:
        {
            "success": bool,
            "post": {
                "post_id": str,
                "platform": str,
                "url": str,
                "title": str,
                "content": str,
                "author": str,
                "created_at": str,
                "engagement": {...},
                "comments": [...],
                "media_urls": [...],
                "tags": [...]
            },
            "raw_content": str,
            "error": str (if failed)
        }
    """
    try:
        service = social_media_crawler_service
        result = await service.crawl_post_detail(
            url=url,
            platform=platform,
            extract_comments=extract_comments,
            max_comments=max_comments,
        )
        return result
    except Exception as e:
        logger.error(f"Crawl post detail failed: {str(e)}")
        return {"success": False, "error": str(e)}


# ============================================================================
# AI Evaluation Endpoints
# ============================================================================


@router.post("/ai/evaluate/relevance")
async def evaluate_relevance(
    content: str,
    product_description: str,
    language: str = "zh",
):
    """
    AI 评判内容相关性。

    纯粹的能力提供 - n8n 负责决定后续处理逻辑。

    Args:
        content: 待评判的内容
        product_description: 产品描述
        language: 语言 "zh" 或 "en"

    Returns:
        {
            "is_relevant": bool,
            "relevance_score": float (0-1),
            "confidence": float (0-1),
            "reasoning": str,
            "suggested_angle": str (可选)
        }
    """
    try:
        service = langchain_agent_service
        result = service.evaluate_relevance(
            content=content,
            product_description=product_description,
            language=language,
        )
        return {"success": True, **result}
    except Exception as e:
        logger.error(f"Evaluate relevance failed: {str(e)}")
        return {"success": False, "error": str(e)}


# ============================================================================
# AI Generation Endpoints
# ============================================================================


@router.post("/ai/generate/reply")
async def generate_reply(
    original_content: str,
    platform: str = "reddit",
    tone: str = "professional",
    language: str = "zh",
    product_info: Optional[str] = None,
):
    """
    AI 生成回复内容。

    纯粹的能力提供 - n8n 负责后续审核和发布。

    Args:
        original_content: 原始帖子内容
        platform: 目标平台 "reddit", "twitter", "linkedin", "xhs" 等
        tone: 语气 "professional", "friendly", "casual"
        language: 语言 "zh" 或 "en"
        product_info: 产品信息（可选）

    Returns:
        {
            "reply": str,
            "confidence": float,
            "platform": str,
            "suggested_tags": list (可选)
        }
    """
    try:
        service = langchain_agent_service
        result = service.generate_reply(
            original_content=original_content,
            platform=platform,
            tone=tone,
            language=language,
            product_info=product_info,
        )
        return {"success": True, **result}
    except Exception as e:
        logger.error(f"Generate reply failed: {str(e)}")
        return {"success": False, "error": str(e)}


@router.post("/ai/generate/article", response_model=ArticleGenerationResponse)
async def generate_article(request: ArticleGenerationRequest) -> ArticleGenerationResponse:
    """生成营销文章。

    使用 LangChain 和 LLM 生成高质量的营销文章。

    Args:
        request: 文章生成请求

    Returns:
        文章生成响应

    Example:
        ```bash
        POST /api/v1/ai/generate/article
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


@router.post("/ai/generate/articles/batch")
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


@router.post("/ai/generate/optimize", response_model=SEOOptimizationResponse)
async def optimize_content(request: SEOOptimizationRequest) -> SEOOptimizationResponse:
    """优化文章的 SEO 表现。

    分析并优化现有文章的搜索引擎优化。

    Args:
        request: SEO 优化请求

    Returns:
        SEO 优化响应

    Example:
        ```bash
        POST /api/v1/ai/generate/optimize
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


@router.get("/ai/status")
async def get_ai_status():
    """获取 AI 内容生成服务状态。

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


# ============================================================================
# Publisher Endpoints - 发布能力
# ============================================================================


@router.post("/publisher/post")
async def publish_post(
    platform: str,
    content: str,
    title: Optional[str] = None,
    subreddit: Optional[str] = None,
):
    """
    发布帖子到社交媒体平台。

    支持平台：Reddit, Twitter, LinkedIn

    Args:
        platform: 目标平台 (reddit, twitter, linkedin)
        content: 帖子内容
        title: 标题（Reddit 必需）
        subreddit: Subreddit 名称（Reddit 必需）

    Returns:
        {
            "success": bool,
            "post_id": str,
            "post_url": str,
            "platform": str,
            "error": str (if failed)
        }
    """
    try:
        from app.services.publisher_service import publisher_service

        result = await publisher_service.publish_post(
            platform=platform,
            content=content,
            title=title,
            subreddit=subreddit,
        )
        return result
    except Exception as e:
        logger.error(f"Publish post failed: {str(e)}")
        return {"success": False, "error": str(e)}


@router.post("/publisher/comment")
async def publish_comment(
    platform: str,
    post_url: str,
    content: str,
    parent_comment_id: Optional[str] = None,
):
    """
    发布评论/回复到社交媒体平台。

    支持平台：Reddit, Twitter, LinkedIn

    Args:
        platform: 目标平台 (reddit, twitter, linkedin)
        post_url: 目标帖子 URL
        content: 评论内容
        parent_comment_id: 父评论 ID（用于回复评论，可选）

    Returns:
        {
            "success": bool,
            "comment_id": str,
            "comment_url": str,
            "platform": str,
            "error": str (if failed)
        }
    """
    try:
        from app.services.publisher_service import publisher_service

        result = await publisher_service.publish_comment(
            platform=platform,
            post_url=post_url,
            content=content,
            parent_comment_id=parent_comment_id,
        )
        return result
    except Exception as e:
        logger.error(f"Publish comment failed: {str(e)}")
        return {"success": False, "error": str(e)}
