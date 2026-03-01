"""社交媒体爬虫服务 - 使用 crawl4ai 实时爬取社交媒体内容。"""

import json
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

from app.models.db import SocialMediaPost, SearchSession
from app.core.logging import get_logger
from app.core.config import get_settings

logger = get_logger(__name__)


class SocialMediaCrawlerService:
    """社交媒体爬虫服务 - 使用 crawl4ai 实时爬取。"""

    def __init__(self):
        self.settings = get_settings()

    async def crawl_with_crawl4ai(
        self,
        db: Session,
        keyword: str,
        platforms: List[str],
        max_results: int = 30,
        universe_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """使用 crawl4ai 实时爬取社交媒体内容。

        这是核心业务流程：
        1. 根据关键词在社交媒体平台搜索
        2. 使用 crawl4ai 爬取页面内容
        3. 实时返回内容给调用方（不是从数据库查询）

        Args:
            db: 数据库会话
            keyword: 搜索关键词
            platforms: 平台列表 (e.g., ["reddit", "twitter"])
            max_results: 最大结果数
            universe_id: 关键词宇宙 ID（用于记录）

        Returns:
            爬取结果字典
        """
        search_session_id = f"search_{datetime.utcnow().timestamp()}"
        results = []

        try:
            # 创建搜索会话记录
            search_session = SearchSession(
                id=search_session_id,
                universe_id=universe_id,
                keyword=keyword,
                platforms=json.dumps(platforms),
                pages=1,
                status="in_progress",
            )
            db.add(search_session)
            db.commit()

            # 为每个平台构建搜索 URL 并爬取
            platform_urls = self._build_search_urls(keyword, platforms)

            for platform, url in platform_urls.items():
                try:
                    # 使用 crawl4ai 爬取页面
                    result = await self._crawl_single_page(url, platform)

                    if result and result.success:
                        # 解析并提取帖子内容
                        posts = self._extract_posts_from_page(result, platform, keyword)

                        # 保存到数据库（仅用于历史记录）
                        for post_data in posts:
                            self._save_post_to_db(db, post_data)

                        results.extend(posts)
                        logger.info(f"Crawled {len(posts)} posts from {platform}")

                except Exception as e:
                    logger.error(f"Error crawling {platform}: {str(e)}")

            # 更新搜索会话
            search_session.status = "completed"
            search_session.total_results = len(results)
            search_session.completed_at = datetime.utcnow()
            db.commit()

            return {
                "success": True,
                "search_id": search_session_id,
                "keyword": keyword,
                "total_results": len(results),
                "posts": results,
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Crawl failed for keyword '{keyword}': {str(e)}")
            return {
                "success": False,
                "error": str(e),
            }

    async def _crawl_single_page(self, url: str, platform: str):
        """使用 crawl4ai 爬取单个页面。

        这是 crawl4ai 的真实用法：
        - 使用 AsyncWebCrawler
        - 调用 arun() 方法
        - 返回包含 markdown 和其他数据的 result 对象
        """
        try:
            browser_config = BrowserConfig(
                headless=True,
                verbose=False,
            )

            run_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
            )

            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await crawler.arun(
                    url=url,
                    config=run_config,
                )
                return result

        except Exception as e:
            logger.error(f"crawl4ai failed for {url}: {str(e)}")
            raise

    def _build_search_urls(self, keyword: str, platforms: List[str]) -> Dict[str, str]:
        """为不同平台构建搜索 URL。

        Args:
            keyword: 搜索关键词
            platforms: 平台列表

        Returns:
            {平台名: 搜索URL} 的字典
        """
        urls = {}

        # Reddit 搜索 URL
        if "reddit" in platforms:
            urls["reddit"] = f"https://www.reddit.com/search/?q={keyword}&type=posts"

        # Twitter/X 搜索 URL (需要登录)
        if "twitter" in platforms:
            urls["twitter"] = f"https://twitter.com/search?q={keyword}&src=typed_query"

        # LinkedIn 搜索 URL
        if "linkedin" in platforms:
            urls["linkedin"] = (
                f"https://www.linkedin.com/search/results/content/?keywords={keyword}"
            )

        return urls

    def _extract_posts_from_page(
        self, crawl_result, platform: str, keyword: str
    ) -> List[Dict[str, Any]]:
        """从 crawl4ai 的结果中提取帖子信息。

        这是一个简化的实现 - 实际应该根据不同平台的 HTML 结构解析

        Args:
            crawl_result: crawl4ai 的 CrawlResult 对象
            platform: 平台名称
            keyword: 搜索关键词

        Returns:
            帖子数据列表
        """
        posts = []
        markdown = crawl_result.markdown

        # 简化的解析逻辑 - 实际实现需要根据各平台的 HTML 结构解析
        # 这里只是演示概念

        if platform == "reddit" and markdown:
            # 从 markdown 中提取 Reddit 帖子
            lines = markdown.split("\n")
            current_post = None

            for line in lines:
                if line.startswith("# ") or line.startswith("## "):
                    # 新帖子标题
                    if current_post:
                        posts.append(current_post)
                    current_post = {
                        "post_id": f"{platform}_{len(posts)}_{datetime.utcnow().timestamp()}",
                        "platform": platform,
                        "title": line.lstrip("#").strip(),
                        "content": "",
                        "author": "unknown",
                        "url": crawl_result.url,
                        "engagement": {},
                        "created_at": datetime.utcnow(),
                    }
                elif current_post and line.strip():
                    # 帖子内容
                    current_post["content"] += line + "\n"

            if current_post:
                posts.append(current_post)

        return posts

    def _save_post_to_db(self, db: Session, post_data: Dict[str, Any]):
        """将爬取的帖子保存到数据库（仅用于历史记录）。

        注意：这不是业务流程的一部分，只是保存历史
        """
        try:
            post = SocialMediaPost(
                id=post_data.get("post_id"),
                post_id=post_data.get("post_id"),
                platform=post_data.get("platform"),
                title=post_data.get("title"),
                content=post_data.get("content"),
                author=post_data.get("author"),
                url=post_data.get("url"),
                engagement=json.dumps(post_data.get("engagement", {})),
                created_at=post_data.get("created_at"),
            )
            db.add(post)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to save post to database: {str(e)}")
            db.rollback()


# 创建全局单例实例
social_media_crawler_service = SocialMediaCrawlerService()
