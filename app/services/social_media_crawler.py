"""社交媒体爬虫服务 - 使用本地部署的 crawl4ai 实时爬取社交媒体内容。"""

import json
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime

from app.core.logging import get_logger
from app.core.config import get_settings
from app.services.state_store import state_store

logger = get_logger(__name__)


MEDIACRAWLER_PLATFORMS = ["tieba", "xhs", "dy", "bili", "zhihu", "zhihu", "douyin"]


class SocialMediaCrawlerService:
    """社交媒体爬虫服务 - 使用本地部署的 crawl4ai API 实时爬取。"""

    def __init__(self):
        self.settings = get_settings()
        self.crawl4ai_url = self.settings.crawl4ai_api_url
        self.crawl4ai_timeout = self.settings.crawl4ai_timeout
        self.mediacrawler_url = self.settings.mediacrawler_api_url
        self.mediacrawler_timeout = self.settings.mediacrawler_timeout
        self.mediacrawler_max_retries = self.settings.mediacrawler_max_retries
        self.mediacrawler_poll_interval = self.settings.mediacrawler_poll_interval

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

    async def crawl_with_mediacrawler(
        self,
        keyword: str,
        platform: str = "tieba",
        max_results: int = 10,
    ) -> Dict[str, Any]:
        """使用 MediaCrawler API 进行异步爬取。

        流程：
        1. 调用 MediaCrawler /api/crawler/start 启动任务
        2. 轮询任务状态直到完成
        3. 获取爬虫结果
        4. 返回结果给调用方

        Args:
            keyword: 搜索关键词
            platform: 平台类型 (tieba, xhs, dy, bili, zhihu)
            max_results: 最大结果数

        Returns:
            搜索结果字典
        """
        import time

        search_session_id = f"mc_{platform}_{datetime.utcnow().timestamp()}"

        try:
            state_store.save_search_session(
                session_id=search_session_id,
                session_data={
                    "keyword": keyword,
                    "platform": platform,
                    "status": "in_progress",
                    "created_at": datetime.utcnow().isoformat(),
                    "max_results": max_results,
                },
            )

            start_response = await self._call_mediacrawler_api(
                endpoint="/api/crawler/start",
                method="POST",
                payload={
                    "platform": platform,
                    "type": "search",
                    "keyword": keyword,
                    "config": {"max_results": max_results},
                },
            )

            if not start_response or not start_response.get("task_id"):
                error_msg = start_response.get("error", "Failed to start MediaCrawler task")
                logger.error(f"Failed to start MediaCrawler task: {error_msg}")
                state_store.save_search_session(
                    session_id=search_session_id,
                    session_data={
                        "status": "failed",
                        "error_message": error_msg,
                        "completed_at": datetime.utcnow().isoformat(),
                    },
                )
                return {
                    "success": False,
                    "error": error_msg,
                    "search_id": search_session_id,
                }

            task_id = start_response["task_id"]
            logger.info(f"MediaCrawler task started: {task_id}, polling for results...")

            task_result = await self._wait_for_mediacrawler_task(task_id)

            if not task_result or not task_result.get("success"):
                error_msg = task_result.get("error", "Task failed or timed out")
                logger.error(f"MediaCrawler task failed: {task_id}, error: {error_msg}")
                state_store.save_search_session(
                    session_id=search_session_id,
                    session_data={
                        "status": "failed",
                        "error_message": error_msg,
                        "completed_at": datetime.utcnow().isoformat(),
                    },
                )
                return {
                    "success": False,
                    "error": error_msg,
                    "search_id": search_session_id,
                }

            posts = task_result.get("posts", [])
            logger.info(f"MediaCrawler task completed: {task_id}, got {len(posts)} posts")

            state_store.save_search_session(
                session_id=search_session_id,
                session_data={
                    "status": "completed",
                    "total_results": len(posts),
                    "completed_at": datetime.utcnow().isoformat(),
                },
            )

            return {
                "success": True,
                "search_id": search_session_id,
                "keyword": keyword,
                "platform": platform,
                "total_results": len(posts),
                "posts": posts,
            }

        except Exception as e:
            logger.error(f"MediaCrawler crawl failed for keyword '{keyword}': {str(e)}")
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

    async def _call_mediacrawler_api(
        self,
        endpoint: str,
        method: str = "POST",
        payload: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """调用 MediaCrawler API。

        Args:
            endpoint: API 端点路径
            method: HTTP 方法
            payload: 请求体 JSON 数据
            params: URL 查询参数

        Returns:
            API 响应数据
        """
        import requests

        url = f"{self.mediacrawler_url}{endpoint}"
        max_attempts = self.mediacrawler_max_retries

        for attempt in range(max_attempts):
            try:
                if method == "POST":
                    response = requests.post(
                        url,
                        json=payload,
                        timeout=self.mediacrawler_timeout,
                    )
                else:
                    response = requests.get(
                        url,
                        params=params,
                        timeout=self.mediacrawler_timeout,
                    )

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 503:
                    logger.warning(
                        f"MediaCrawler service unavailable, attempt {attempt + 1}/{max_attempts}"
                    )
                    time.sleep(2)
                else:
                    logger.error(
                        f"MediaCrawler API returned status {response.status_code}: {response.text}"
                    )
                    return {"error": f"HTTP {response.status_code}", "detail": response.text}

            except requests.exceptions.ConnectionError:
                logger.warning(
                    f"Cannot connect to MediaCrawler, attempt {attempt + 1}/{max_attempts}"
                )
                time.sleep(2)
            except requests.exceptions.Timeout:
                logger.warning(f"MediaCrawler API timeout, attempt {attempt + 1}/{max_attempts}")
                time.sleep(2)
            except Exception as e:
                logger.error(f"Error calling MediaCrawler API: {str(e)}")
                return {"error": str(e)}

        return {"error": "MediaCrawler service unavailable after retries"}

    async def _wait_for_mediacrawler_task(
        self,
        task_id: str,
        max_wait_time: int = 60,
    ) -> Optional[Dict[str, Any]]:
        """轮询等待 MediaCrawler 任务完成。

        Args:
            task_id: 任务 ID
            max_wait_time: 最大等待时间（秒）

        Returns:
            任务结果数据
        """
        import time

        elapsed = 0
        poll_interval = self.mediacrawler_poll_interval

        while elapsed < max_wait_time:
            try:
                status_response = await self._call_mediacrawler_api(
                    endpoint=f"/api/data/tasks/{task_id}",
                    method="GET",
                )

                if not status_response:
                    time.sleep(poll_interval)
                    elapsed += poll_interval
                    continue

                status = status_response.get("status", "")

                if status == "completed":
                    return await self._get_mediacrawler_results(task_id)
                elif status == "failed":
                    error_msg = status_response.get("error", "Task failed")
                    logger.error(f"MediaCrawler task {task_id} failed: {error_msg}")
                    return {"success": False, "error": error_msg}
                elif status == "running":
                    logger.debug(f"MediaCrawler task {task_id} still running...")
                else:
                    logger.warning(f"Unknown task status: {status}")

                time.sleep(poll_interval)
                elapsed += poll_interval

            except Exception as e:
                logger.error(f"Error polling MediaCrawler task {task_id}: {str(e)}")
                time.sleep(poll_interval)
                elapsed += poll_interval

        logger.warning(f"MediaCrawler task {task_id} timed out after {max_wait_time}s")
        return {"success": False, "error": f"Task timed out after {max_wait_time}s"}

    async def _get_mediacrawler_results(self, task_id: str) -> Dict[str, Any]:
        """获取 MediaCrawler 爬虫结果。

        Args:
            task_id: 任务 ID

        Returns:
            解析后的帖子数据
        """
        try:
            results_response = await self._call_mediacrawler_api(
                endpoint="/api/data/results",
                method="GET",
                params={"task_id": task_id},
            )

            if not results_response:
                return {"success": False, "error": "No results returned"}

            raw_results = results_response.get("data", [])
            posts = self._parse_mediacrawler_results(raw_results)

            return {
                "success": True,
                "posts": posts,
                "total": len(posts),
            }

        except Exception as e:
            logger.error(f"Error getting MediaCrawler results: {str(e)}")
            return {"success": False, "error": str(e)}

    def _parse_mediacrawler_results(
        self, raw_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """解析 MediaCrawler 返回的原始数据。

        Args:
            raw_results: MediaCrawler API 返回的原始结果

        Returns:
            标准化后的帖子列表
        """
        posts = []

        for item in raw_results:
            post = {
                "post_id": item.get("id") or item.get("post_id") or f"mc_{len(posts)}",
                "title": item.get("title", ""),
                "author": item.get("author") or item.get("user") or item.get("username", "unknown"),
                "content": item.get("content") or item.get("text") or item.get("description", ""),
                "url": item.get("url") or item.get("link", ""),
                "platform": item.get("platform", ""),
                "created_at": item.get("created_at")
                or item.get("publish_time")
                or item.get("time"),
            }

            if "forum_name" in item:
                post["forum_name"] = item["forum_name"]
            if "reply_count" in item:
                post["reply_count"] = item["reply_count"]
            if "like_count" in item or "likes" in item:
                post["like_count"] = item.get("like_count") or item.get("likes", 0)
            if "share_count" in item or "shares" in item:
                post["share_count"] = item.get("share_count") or item.get("shares", 0)
            if "comment_count" in item:
                post["comment_count"] = item["comment_count"]

            if item.get("media"):
                post["media_urls"] = (
                    item["media"] if isinstance(item["media"], list) else [item["media"]]
                )

            posts.append(post)

        return posts

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

    async def get_post_detail_from_mediacrawler(
        self,
        post_url: str,
        platform: str = "tieba",
        extract_comments: bool = False,
        max_comments: int = 10,
    ) -> Dict[str, Any]:
        """使用 MediaCrawler API 获取帖子详情。

        流程：
        1. 调用 MediaCrawler /api/crawler/start 启动详情爬取任务
        2. 轮询任务状态直到完成
        3. 获取爬虫结果
        4. 返回详情给调用方

        Args:
            post_url: 帖子 URL
            platform: 平台类型 (tieba, xhs, dy, bili, zhihu)
            extract_comments: 是否提取评论
            max_comments: 最大评论数

        Returns:
            {
                "success": bool,
                "post": {
                    "post_id": str,
                    "title": str,
                    "author": str,
                    "content": str,
                    "forum_name": str,
                    "url": str,
                    "reply_count": int,
                    "media_urls": list
                },
                "comments": list,
                "error": str (if failed)
            }
        """
        import time

        try:
            logger.info(f"Getting post detail from MediaCrawler: {post_url} (platform: {platform})")

            # 启动详情爬取任务
            start_response = await self._call_mediacrawler_api(
                endpoint="/api/crawler/start",
                method="POST",
                payload={
                    "platform": platform,
                    "type": "detail",
                    "config": {
                        "post_urls": [post_url],
                        "max_comments": max_comments,
                    },
                },
            )

            if not start_response or not start_response.get("task_id"):
                error_msg = start_response.get("error", "Failed to start MediaCrawler detail task")
                logger.error(f"Failed to start MediaCrawler detail task: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "url": post_url,
                }

            task_id = start_response["task_id"]
            logger.info(f"MediaCrawler detail task started: {task_id}, polling for results...")

            # 轮询等待任务完成
            task_result = await self._wait_for_mediacrawler_task(task_id, max_wait_time=120)

            if not task_result or not task_result.get("success"):
                error_msg = task_result.get("error", "Detail task failed or timed out")
                logger.error(f"MediaCrawler detail task failed: {task_id}, error: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "url": post_url,
                }

            # 解析帖子详情
            raw_posts = task_result.get("posts", [])
            if not raw_posts:
                return {
                    "success": False,
                    "error": "No post data returned",
                    "url": post_url,
                }

            post_data = raw_posts[0] if raw_posts else {}
            comments = []

            # 提取评论（如果需要）
            if extract_comments:
                comments = post_data.get("comments", [])[:max_comments]

            # 构建标准化响应
            post_detail = {
                "post_id": post_data.get("post_id") or post_data.get("id") or f"mc_{task_id}",
                "title": post_data.get("title", ""),
                "author": post_data.get("author") or post_data.get("user", "unknown"),
                "content": post_data.get("content") or post_data.get("text", ""),
                "forum_name": post_data.get("forum_name", ""),
                "url": post_data.get("url") or post_url,
                "reply_count": post_data.get("reply_count") or post_data.get("comment_count", 0),
                "media_urls": post_data.get("media_urls", [])
                if isinstance(post_data.get("media_urls"), list)
                else [],
            }

            # 添加可选字段
            if post_data.get("like_count"):
                post_detail["like_count"] = post_data.get("like_count")
            if post_data.get("created_at"):
                post_detail["created_at"] = post_data.get("created_at")

            logger.info(
                f"MediaCrawler detail task completed: {task_id}, got post: {post_detail.get('title', '')[:50]}"
            )

            return {
                "success": True,
                "post": post_detail,
                "comments": comments,
            }

        except Exception as e:
            logger.error(f"Failed to get post detail from MediaCrawler: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "url": post_url,
            }

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
