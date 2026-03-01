"""社交媒体爬虫服务 - 使用本地部署的 crawl4ai 实时爬取社交媒体内容。"""

import json
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.db import SocialMediaPost, SearchSession
from app.core.logging import get_logger
from app.core.config import get_settings

logger = get_logger(__name__)


class SocialMediaCrawlerService:
    """社交媒体爬虫服务 - 使用本地部署的 crawl4ai API 实时爬取。"""

    def __init__(self):
        self.settings = get_settings()
        self.crawl4ai_url = self.settings.crawl4ai_api_url
        self.crawl4ai_timeout = self.settings.crawl4ai_timeout

    async def crawl_with_crawl4ai(
        self,
        db: Session,
        keyword: str,
        platforms: List[str],
        max_results: int = 30,
        universe_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """使用本地部署的 crawl4ai API 实时爬取社交媒体内容。

        这是核心业务流程：
        1. 根据关键词在社交媒体平台搜索
        2. 调用本地部署的 crawl4ai API 爬取页面内容
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
                    # 调用本地部署的 crawl4ai API
                    result = self._call_crawl4ai_api(url)

                    if result and result.get("success"):
                        # 解析并提取帖子内容
                        posts = self._extract_posts_from_result(result, platform, keyword)

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

    def _call_crawl4ai_api(self, url: str) -> Optional[Dict[str, Any]]:
        """调用本地部署的 crawl4ai API。

        Args:
            url: 要爬取的 URL

        Returns:
            crawl4ai 的响应结果
        """
        try:
            payload = {
                "urls": [url],
                "priority": 10,
            }

            response = requests.post(
                f"{self.crawl4ai_url}/crawl",
                json=payload,
                timeout=self.crawl4ai_timeout,
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("results"):
                    # 返回第一个结果
                    return {
                        "success": True,
                        "markdown": data["results"][0].get("markdown", ""),
                        "url": url,
                    }
                elif data.get("task_id"):
                    # 如果是异步任务，等待结果
                    return self._wait_for_crawl_result(data["task_id"])
            else:
                logger.error(f"Crawl4AI API returned status {response.status_code}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to call crawl4ai API: {str(e)}")
            return None

        return None

    def _wait_for_crawl_result(
        self, task_id: str, max_attempts: int = 10
    ) -> Optional[Dict[str, Any]]:
        """等待 crawl4ai 异步任务完成。

        Args:
            task_id: 任务 ID
            max_attempts: 最大尝试次数

        Returns:
            爬取结果
        """
        import time

        for attempt in range(max_attempts):
            try:
                response = requests.get(
                    f"{self.crawl4ai_url}/task/{task_id}",
                    timeout=5,
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "completed" and data.get("results"):
                        return {
                            "success": True,
                            "markdown": data["results"][0].get("markdown", ""),
                            "url": data["results"][0].get("url", ""),
                        }
                    elif data.get("status") == "failed":
                        logger.error(f"Crawl4AI task {task_id} failed")
                        return None

                time.sleep(1)

            except Exception as e:
                logger.error(f"Error waiting for crawl4ai task {task_id}: {str(e)}")

        return None

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

    def _extract_posts_from_result(
        self, crawl_result: Dict[str, Any], platform: str, keyword: str
    ) -> List[Dict[str, Any]]:
        """从 crawl4ai 的结果中提取帖子信息。

        Args:
            crawl_result: crawl4ai 的响应结果
            platform: 平台名称
            keyword: 搜索关键词

        Returns:
            帖子数据列表
        """
        posts = []
        markdown = crawl_result.get("markdown", "")

        if not markdown:
            return posts

        # 简化的解析逻辑 - 实际实现需要根据各平台的 HTML/Markdown 结构解析
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
                    "url": crawl_result.get("url", ""),
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
