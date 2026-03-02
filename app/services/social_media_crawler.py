"""社交媒体爬虫服务 - 使用本地部署的 crawl4ai 实时爬取社交媒体内容。"""

import json
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime

from app.core.logging import get_logger
from app.core.config import get_settings
from app.services.state_store import state_store

logger = get_logger(__name__)


class SocialMediaCrawlerService:
    """社交媒体爬虫服务 - 使用本地部署的 crawl4ai API 实时爬取。"""

    def __init__(self):
        self.settings = get_settings()
        self.crawl4ai_url = self.settings.crawl4ai_api_url
        self.crawl4ai_timeout = self.settings.crawl4ai_timeout

    async def crawl_with_crawl4ai(
        self,
        keyword: str,
        platforms: List[str],
        max_results: int = 30,
        resume_from_checkpoint: bool = True,
    ) -> Dict[str, Any]:
        """使用本地部署的 crawl4ai API 实时爬取社交媒体内容。

        这是核心业务流程：
        1. 根据关键词在社交媒体平台搜索
        2. 调用本地部署的 crawl4ai API 爬取页面内容
        3. 实时返回内容给调用方（不使用数据库）
        4. 保存状态到文件系统用于崩溃恢复

        Args:
            keyword: 搜索关键词
            platforms: 平台列表 (e.g., ["reddit", "twitter", "xhs"])
            max_results: 最大结果数
            resume_from_checkpoint: 是否尝试从检查点恢复

        Returns:
            爬取结果字典
        """
        # 生成唯一的搜索会话 ID
        search_session_id = f"search_{datetime.utcnow().timestamp()}"
        results = []

        try:
            # 创建搜索会话记录
            state_store.save_search_session(
                search_session_id=search_session_id,
                session_data={
                    "keyword": keyword,
                    "platforms": platforms,
                    "status": "in_progress",
                    "current_page": 1,
                    "total_results": 0,
                    "relevant_count": 0,
                    "created_at": datetime.utcnow().isoformat(),
                    "max_results": max_results,
                },
            )

            # 尝试从检查点恢复
            last_checkpoint = None
            if resume_from_checkpoint:
                last_checkpoint = state_store.load_last_checkpoint(
                    session_id=search_session_id, checkpoint_type="page"
                )

            start_page = 1
            if last_checkpoint:
                start_page = last_checkpoint.get("page_number", 1) + 1
                logger.info(f"Resuming from checkpoint: page {start_page}")

            # 为每个平台构建搜索 URL 并爬取
            platform_urls = self._build_search_urls(keyword, platforms)

            for platform, url in platform_urls.items():
                try:
                    # 调用本地部署的 crawl4ai API
                    result = self._call_crawl4ai_api(url)

                    if result and result.get("success"):
                        # 解析并提取帖子内容
                        posts = self._extract_posts_from_result(result, platform, keyword)

                        results.extend(posts)
                        logger.info(f"Crawled {len(posts)} posts from {platform}")

                        # 保存每页检查点
                        state_store.save_crawl_checkpoint(
                            session_id=search_session_id,
                            platform=platform,
                            page_number=start_page,
                            cursor=None,
                            processed_count=len(posts),
                            failed_count=0,
                            checkpoint_type="page",
                        )

                    else:
                        # 记录失败
                        logger.error(f"Failed to crawl {platform}")
                        state_store.save_failed_item(
                            session_id=search_session_id,
                            item_id=f"{platform}_page_{start_page}",
                            item_data={"url": url},
                            error_message=f"Crawl failed: {result.get('error', 'Unknown')}",
                        )

                except Exception as e:
                    logger.error(f"Error crawling {platform}: {str(e)}")
                    state_store.save_failed_item(
                        session_id=search_session_id,
                        item_id=f"{platform}_page_{start_page}",
                        item_data={"url": url},
                        error_message=str(e),
                    )

            # 更新搜索会话状态
            state_store.save_search_session(
                session_id=search_session_id,
                session_data={
                    "status": "completed",
                    "total_results": len(results),
                    "completed_at": datetime.utcnow().isoformat(),
                },
            )

            # 清理检查点
            state_store.cleanup_checkpoints(search_session_id, keep_days=1)

            return {
                "success": True,
                "search_id": search_session_id,
                "keyword": keyword,
                "total_results": len(results),
                "results_per_platform": {"all": results},
            }

        except Exception as e:
            logger.error(f"Crawl failed for keyword '{keyword}': {str(e)}")

            # 标记会话失败
            state_store.save_search_session(
                session_id=search_session_id,
                session_data={
                    "status": "failed",
                    "error_message": str(e),
                    "completed_at": datetime.utcnow().isoformat(),
                },
            )

            return {
                "success": False,
                "error": str(e),
                "search_id": search_session_id,
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

    async def crawl_post_detail(
        self,
        url: str,
        platform: str,
        extract_comments: bool = False,
        max_comments: int = 10,
    ) -> Dict[str, Any]:
        """爬取单个帖子的详细内容。

        Args:
            url: 帖子 URL
            platform: 平台类型 (reddit, twitter, linkedin, xhs, dy, bili, zhihu)
            extract_comments: 是否提取评论
            max_comments: 最大评论数

        Returns:
            帖子详情字典
        """
        try:
            # 调用 crawl4ai API 爬取帖子页面
            result = self._call_crawl4ai_api(url)

            if not result or not result.get("success"):
                return {
                    "success": False,
                    "error": "Failed to crawl post",
                    "url": url,
                }

            markdown = result.get("markdown", "")

            # 根据平台解析帖子详情
            post_detail = self._parse_post_detail(markdown, url, platform)

            if extract_comments:
                comments = self._extract_comments(markdown, platform, max_comments)
                post_detail["comments"] = comments

            return {
                "success": True,
                "post": post_detail,
                "raw_content": markdown,
            }

        except Exception as e:
            logger.error(f"Failed to crawl post detail: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "url": url,
            }

    def _parse_post_detail(
        self,
        markdown: str,
        url: str,
        platform: str,
    ) -> Dict[str, Any]:
        """从 Markdown 内容中解析帖子详情。

        Args:
            markdown: 爬取的 Markdown 内容
            url: 帖子 URL
            platform: 平台类型

        Returns:
            结构化的帖子详情
        """
        from app.models.schemas import PostEngagement

        # 生成帖子 ID
        post_id = f"{platform}_{datetime.utcnow().timestamp()}"

        # 基础解析逻辑
        lines = markdown.split("\n")
        title = None
        content_lines = []
        author = "unknown"

        for i, line in enumerate(lines):
            # 提取标题
            if i == 0 and line.startswith("# "):
                title = line.lstrip("#").strip()
                continue

            # 提取作者（简化逻辑，实际需根据平台调整）
            if "author:" in line.lower() or "by:" in line.lower():
                author = line.split(":")[-1].strip()
                continue

            # 收集内容
            if line.strip():
                content_lines.append(line)

        content = "\n".join(content_lines)

        # 构建帖子详情
        post_detail = {
            "post_id": post_id,
            "platform": platform,
            "url": url,
            "title": title,
            "content": content,
            "author": author,
            "author_id": None,
            "author_url": None,
            "created_at": None,
            "engagement": PostEngagement().model_dump(),
            "comments": [],
            "media_urls": [],
            "tags": [],
        }

        # 平台特定解析
        if platform == "reddit":
            post_detail.update(self._parse_reddit_post(markdown, url))
        elif platform == "twitter":
            post_detail.update(self._parse_twitter_post(markdown, url))
        elif platform == "linkedin":
            post_detail.update(self._parse_linkedin_post(markdown, url))

        return post_detail

    def _parse_reddit_post(self, markdown: str, url: str) -> Dict[str, Any]:
        """解析 Reddit 帖子详情。"""
        result = {"subreddit": None}

        # 从 URL 提取 subreddit
        if "reddit.com/r/" in url:
            parts = url.split("/r/")
            if len(parts) > 1:
                subreddit = parts[1].split("/")[0]
                result["subreddit"] = subreddit

        # 提取互动数据（简化逻辑）
        if "upvote" in markdown.lower():
            result["engagement"] = {"upvotes": 0, "comments_count": 0}

        return result

    def _parse_twitter_post(self, markdown: str, url: str) -> Dict[str, Any]:
        """解析 Twitter/X 推文详情。"""
        result = {}

        # 简化解析逻辑
        if "reply" in markdown.lower() or "replies" in markdown.lower():
            result["engagement"] = {"likes": 0, "retweets": 0, "comments_count": 0}

        return result

    def _parse_linkedin_post(self, markdown: str, url: str) -> Dict[str, Any]:
        """解析 LinkedIn 帖子详情。"""
        result = {}

        # 简化解析逻辑
        if "like" in markdown.lower():
            result["engagement"] = {"likes": 0, "comments_count": 0, "shares": 0}

        return result

    def _extract_comments(
        self,
        markdown: str,
        platform: str,
        max_comments: int,
    ) -> List[Dict[str, Any]]:
        """从 Markdown 中提取评论。

        Args:
            markdown: 爬取的 Markdown 内容
            platform: 平台类型
            max_comments: 最大评论数

        Returns:
            评论列表
        """
        comments = []
        lines = markdown.split("\n")

        # 简化的评论提取逻辑
        current_comment = None
        comment_count = 0

        for line in lines:
            # 检测评论开始（通常以特定格式开始）
            if line.strip().startswith("> ") or "> **" in line:
                if current_comment:
                    comments.append(current_comment)
                    comment_count += 1
                    if comment_count >= max_comments:
                        break

                current_comment = {
                    "comment_id": f"comment_{comment_count}_{datetime.utcnow().timestamp()}",
                    "author": "unknown",
                    "content": line.strip().lstrip(">").strip(),
                    "created_at": None,
                    "upvotes": None,
                }
            elif current_comment and line.strip():
                current_comment["content"] += " " + line.strip()

        if current_comment and comment_count < max_comments:
            comments.append(current_comment)

        return comments


# 创建全局单例实例
social_media_crawler_service = SocialMediaCrawlerService()
