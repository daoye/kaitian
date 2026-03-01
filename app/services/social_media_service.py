"""社交媒体爬虫服务 - 从多个社交媒体平台获取相关内容。"""

import uuid
import json
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.db import SocialMediaPost, SearchSession
from app.core.logging import get_logger
from app.core.config import get_settings

logger = get_logger(__name__)


class SocialMediaPostData:
    """社交媒体帖子数据模型。"""

    def __init__(
        self,
        post_id: str,
        platform: str,
        title: str,
        content: str,
        author: str,
        url: str,
        engagement: Dict[str, Any],
        created_at: datetime,
    ):
        self.post_id = post_id
        self.platform = platform
        self.title = title
        self.content = content
        self.author = author
        self.url = url
        self.engagement = engagement
        self.created_at = created_at


class SocialMediaCrawlerBase(ABC):
    """社交媒体爬虫基类。"""

    @abstractmethod
    def search(self, keyword: str, limit: int = 30, **kwargs) -> List[SocialMediaPostData]:
        """搜索社交媒体内容。

        Args:
            keyword: 搜索关键词
            limit: 结果数量限制
            **kwargs: 平台特定参数

        Returns:
            SocialMediaPostData 列表
        """
        pass

    @abstractmethod
    def get_platform_name(self) -> str:
        """获取平台名称。"""
        pass


class RedditCrawler(SocialMediaCrawlerBase):
    """Reddit 爬虫实现。"""

    def __init__(self):
        self.settings = get_settings()
        # 在实际实现中，这里会初始化 PRAW 客户端
        # 现在仅作演示
        self.client_initialized = False

    def search(self, keyword: str, limit: int = 30, **kwargs) -> List[SocialMediaPostData]:
        """从 Reddit 搜索相关帖子。"""
        # TODO: 实现真实的 Reddit API 调用
        # 这是一个演示实现
        logger.info(f"Searching Reddit for keyword: {keyword}")
        return []

    def get_platform_name(self) -> str:
        return "reddit"


class TwitterCrawler(SocialMediaCrawlerBase):
    """Twitter 爬虫实现。"""

    def __init__(self):
        self.settings = get_settings()
        # 在实际实现中，这里会初始化 Tweepy 客户端
        self.client_initialized = False

    def search(self, keyword: str, limit: int = 30, **kwargs) -> List[SocialMediaPostData]:
        """从 Twitter 搜索相关推文。"""
        # TODO: 实现真实的 Twitter API 调用
        logger.info(f"Searching Twitter for keyword: {keyword}")
        return []

    def get_platform_name(self) -> str:
        return "twitter"


class LinkedInCrawler(SocialMediaCrawlerBase):
    """LinkedIn 爬虫实现。"""

    def __init__(self):
        self.settings = get_settings()
        # 在实际实现中，这里会初始化 LinkedIn API 客户端
        self.client_initialized = False

    def search(self, keyword: str, limit: int = 30, **kwargs) -> List[SocialMediaPostData]:
        """从 LinkedIn 搜索相关文章和讨论。"""
        # TODO: 实现真实的 LinkedIn API 调用
        logger.info(f"Searching LinkedIn for keyword: {keyword}")
        return []

    def get_platform_name(self) -> str:
        return "linkedin"


class SocialMediaService:
    """社交媒体爬虫管理服务。"""

    def __init__(self):
        self.crawlers = {
            "reddit": RedditCrawler(),
            "twitter": TwitterCrawler(),
            "linkedin": LinkedInCrawler(),
        }

    def search_multiple_platforms(
        self,
        db: Session,
        keyword: str,
        platforms: List[str],
        limit_per_platform: int = 10,
        pages: int = 3,
        universe_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """在多个平台上搜索关键词。

        Args:
            db: 数据库会话
            keyword: 搜索关键词
            platforms: 平台列表 ['reddit', 'twitter', 'linkedin']
            limit_per_platform: 每个平台的结果数
            pages: 要获取的页数
            universe_id: 关键词宇宙 ID

        Returns:
            搜索结果字典
        """
        search_session_id = str(uuid.uuid4())
        results_per_platform = {}
        total_results = 0

        try:
            # 创建搜索会话记录
            search_session = SearchSession(
                id=search_session_id,
                universe_id=universe_id,
                keyword=keyword,
                platforms=json.dumps(platforms),
                pages=pages,
                status="in_progress",
            )
            db.add(search_session)
            db.commit()

            # 在每个平台上搜索
            for platform in platforms:
                if platform not in self.crawlers:
                    logger.warning(f"Unsupported platform: {platform}")
                    continue

                try:
                    crawler = self.crawlers[platform]
                    posts_data = crawler.search(
                        keyword,
                        limit=limit_per_platform * pages,
                        pages=pages,
                    )

                    # 将数据保存到数据库
                    db_posts = []
                    for post_data in posts_data:
                        db_post = self._save_post_to_db(db, post_data)
                        if db_post:
                            db_posts.append(db_post)

                    results_per_platform[platform] = {
                        "count": len(db_posts),
                        "posts": [self._post_to_dict(p) for p in db_posts],
                    }
                    total_results += len(db_posts)

                except Exception as e:
                    logger.error(f"Error searching {platform}: {str(e)}")
                    results_per_platform[platform] = {
                        "count": 0,
                        "error": str(e),
                        "posts": [],
                    }

            # 更新搜索会话
            search_session.status = "completed"
            search_session.total_results = total_results
            search_session.completed_at = datetime.utcnow()
            db.commit()

            logger.info(
                f"Search completed for keyword '{keyword}' with {total_results} total results"
            )

            return {
                "success": True,
                "search_id": search_session_id,
                "keyword": keyword,
                "total_results": total_results,
                "results_per_platform": results_per_platform,
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Search failed for keyword '{keyword}': {str(e)}")

            # 更新搜索会话为失败
            session = db.query(SearchSession).filter(SearchSession.id == search_session_id).first()
            if session:
                session.status = "failed"
                session.error_message = str(e)
                db.commit()

            return {
                "success": False,
                "search_id": search_session_id,
                "error": str(e),
            }

    @staticmethod
    def _save_post_to_db(db: Session, post_data: SocialMediaPostData) -> Optional[SocialMediaPost]:
        """将帖子保存到数据库。"""
        try:
            # 检查帖子是否已存在
            existing = (
                db.query(SocialMediaPost)
                .filter(SocialMediaPost.post_id == post_data.post_id)
                .first()
            )

            if existing:
                return existing

            db_post = SocialMediaPost(
                id=str(uuid.uuid4()),
                post_id=post_data.post_id,
                platform=post_data.platform,
                title=post_data.title,
                content=post_data.content,
                author=post_data.author,
                url=post_data.url,
                engagement=json.dumps(post_data.engagement),
                created_at_original=post_data.created_at,
            )
            db.add(db_post)
            db.commit()
            db.refresh(db_post)
            return db_post
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to save post to database: {str(e)}")
            return None

    @staticmethod
    def _post_to_dict(post: SocialMediaPost) -> Dict[str, Any]:
        """将帖子转换为字典。"""
        try:
            engagement = json.loads(post.engagement) if post.engagement else {}
        except json.JSONDecodeError:
            engagement = {}

        return {
            "post_id": post.post_id,
            "platform": post.platform,
            "title": post.title,
            "content": post.content[:200] + "..." if len(post.content) > 200 else post.content,
            "author": post.author,
            "url": post.url,
            "engagement": engagement,
            "created_at": post.created_at_original.isoformat()
            if post.created_at_original
            else None,
        }

    def get_search_history(
        self,
        db: Session,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[List[SearchSession], int]:
        """获取搜索历史。

        Args:
            db: 数据库会话
            limit: 限制数
            offset: 偏移

        Returns:
            (搜索会话列表, 总数)
        """
        query = db.query(SearchSession)
        total = query.count()
        sessions = query.order_by(SearchSession.created_at.desc()).limit(limit).offset(offset).all()
        return sessions, total


# 创建全局单例实例
social_media_service = SocialMediaService()
