"""Publisher Service - 社交媒体发布服务

支持在多个平台发布帖子和评论：
- Reddit: 使用 praw 库
- Twitter/X: 使用 tweepy 库
- LinkedIn: 使用官方 API
"""

from typing import Dict, Any, Optional
from app.core.logging import get_logger
from app.core.config import get_settings

logger = get_logger(__name__)


class PublisherService:
    """社交媒体发布服务"""

    def __init__(self):
        self.settings = get_settings()
        self._reddit_client = None
        self._twitter_client = None
        self._linkedin_client = None

    # ====================
    # Reddit 发布
    # ====================

    def _get_reddit_client(self):
        """获取 Reddit 客户端"""
        if self._reddit_client is None:
            try:
                import praw

                self._reddit_client = praw.Reddit(
                    client_id=self.settings.reddit_client_id,
                    client_secret=self.settings.reddit_client_secret,
                    user_agent=self.settings.reddit_user_agent,
                    username=self.settings.reddit_username,
                    password=self.settings.reddit_password,
                )
                logger.info("Reddit client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Reddit client: {str(e)}")
                raise
        return self._reddit_client

    async def publish_reddit_post(
        self,
        title: str,
        content: str,
        subreddit: str,
    ) -> Dict[str, Any]:
        """在 Reddit 发布帖子

        Args:
            title: 帖子标题
            content: 帖子内容
            subreddit: 目标 subreddit

        Returns:
            发布结果
        """
        try:
            reddit = self._get_reddit_client()
            subreddit_obj = reddit.subreddit(subreddit)
            submission = subreddit_obj.submit(title, selftext=content)

            logger.info(f"Published Reddit post: {submission.id}")

            return {
                "success": True,
                "post_id": submission.id,
                "post_url": f"https://reddit.com{submission.permalink}",
                "platform": "reddit",
            }
        except Exception as e:
            logger.error(f"Failed to publish Reddit post: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "platform": "reddit",
            }

    async def publish_reddit_comment(
        self,
        post_url: str,
        content: str,
        parent_comment_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """在 Reddit 发布评论

        Args:
            post_url: 帖子 URL
            content: 评论内容
            parent_comment_id: 父评论 ID（可选）

        Returns:
            发布结果
        """
        try:
            reddit = self._get_reddit_client()

            if parent_comment_id:
                comment = reddit.comment(parent_comment_id)
                reply = comment.reply(content)
            else:
                submission = reddit.submission(url=post_url)
                reply = submission.reply(content)

            logger.info(f"Published Reddit comment: {reply.id}")

            return {
                "success": True,
                "comment_id": reply.id,
                "comment_url": f"https://reddit.com{reply.permalink}",
                "platform": "reddit",
            }
        except Exception as e:
            logger.error(f"Failed to publish Reddit comment: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "platform": "reddit",
            }

    # ====================
    # Twitter/X 发布
    # ====================

    def _get_twitter_client(self):
        """获取 Twitter 客户端"""
        if self._twitter_client is None:
            try:
                import tweepy

                self._twitter_client = tweepy.Client(
                    consumer_key=self.settings.twitter_consumer_key,
                    consumer_secret=self.settings.twitter_consumer_secret,
                    access_token=self.settings.twitter_access_token,
                    access_token_secret=self.settings.twitter_access_token_secret,
                )
                logger.info("Twitter client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Twitter client: {str(e)}")
                raise
        return self._twitter_client

    async def publish_twitter_post(
        self,
        content: str,
    ) -> Dict[str, Any]:
        """在 Twitter/X 发布推文

        Args:
            content: 推文内容

        Returns:
            发布结果
        """
        try:
            client = self._get_twitter_client()
            response = client.create_tweet(text=content)

            tweet_id = response.data["id"]
            logger.info(f"Published Twitter tweet: {tweet_id}")

            return {
                "success": True,
                "post_id": tweet_id,
                "post_url": f"https://twitter.com/user/status/{tweet_id}",
                "platform": "twitter",
            }
        except Exception as e:
            logger.error(f"Failed to publish Twitter post: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "platform": "twitter",
            }

    async def publish_twitter_comment(
        self,
        post_url: str,
        content: str,
        parent_comment_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """在 Twitter/X 发布回复

        Args:
            post_url: 推文 URL
            content: 回复内容
            parent_comment_id: 父评论 ID（可选）

        Returns:
            发布结果
        """
        try:
            client = self._get_twitter_client()

            if parent_comment_id:
                in_reply_to_tweet_id = parent_comment_id
            else:
                import re

                match = re.search(r"status/(\d+)", post_url)
                if not match:
                    return {
                        "success": False,
                        "error": "Invalid Twitter URL",
                        "platform": "twitter",
                    }
                in_reply_to_tweet_id = match.group(1)

            response = client.create_tweet(text=content, in_reply_to_tweet_id=in_reply_to_tweet_id)

            tweet_id = response.data["id"]
            logger.info(f"Published Twitter reply: {tweet_id}")

            return {
                "success": True,
                "comment_id": tweet_id,
                "comment_url": f"https://twitter.com/user/status/{tweet_id}",
                "platform": "twitter",
            }
        except Exception as e:
            logger.error(f"Failed to publish Twitter comment: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "platform": "twitter",
            }

    # ====================
    # LinkedIn 发布
    # ====================

    def _get_linkedin_client(self):
        """获取 LinkedIn 客户端"""
        if self._linkedin_client is None:
            try:
                self._linkedin_client = {
                    "access_token": self.settings.linkedin_access_token,
                }
                logger.info("LinkedIn client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize LinkedIn client: {str(e)}")
                raise
        return self._linkedin_client

    async def publish_linkedin_post(
        self,
        content: str,
        title: Optional[str] = None,
    ) -> Dict[str, Any]:
        """在 LinkedIn 发布帖子

        Args:
            content: 帖子内容
            title: 标题（可选）

        Returns:
            发布结果
        """
        try:
            import requests

            client = self._get_linkedin_client()
            access_token = client["access_token"]

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            data = {
                "author": f"urn:li:person:{self.settings.linkedin_person_urn}",
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {"text": content},
                        "shareMediaCategory": "NONE",
                    }
                },
                "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
            }

            response = requests.post(
                "https://api.linkedin.com/v2/ugcPosts", headers=headers, json=data
            )

            if response.status_code == 201:
                post_urn = response.headers.get("X-LI-UUID", "")
                logger.info(f"Published LinkedIn post: {post_urn}")

                return {
                    "success": True,
                    "post_id": post_urn,
                    "post_url": f"https://www.linkedin.com/feed/update/{post_urn}",
                    "platform": "linkedin",
                }
            else:
                return {
                    "success": False,
                    "error": f"LinkedIn API error: {response.status_code}",
                    "platform": "linkedin",
                }
        except Exception as e:
            logger.error(f"Failed to publish LinkedIn post: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "platform": "linkedin",
            }

    async def publish_linkedin_comment(
        self,
        post_url: str,
        content: str,
    ) -> Dict[str, Any]:
        """在 LinkedIn 发布评论

        Args:
            post_url: 帖子 URL
            content: 评论内容

        Returns:
            发布结果
        """
        try:
            import requests

            client = self._get_linkedin_client()
            access_token = client["access_token"]

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            data = {
                "actor": f"urn:li:person:{self.settings.linkedin_person_urn}",
                "object": post_url,
                "message": {"text": content},
            }

            response = requests.post(
                "https://api.linkedin.com/v2/socialActions/{urn}/comments",
                headers=headers,
                json=data,
            )

            if response.status_code == 201:
                comment_id = response.json().get("id", "")
                logger.info(f"Published LinkedIn comment: {comment_id}")

                return {
                    "success": True,
                    "comment_id": comment_id,
                    "platform": "linkedin",
                }
            else:
                return {
                    "success": False,
                    "error": f"LinkedIn API error: {response.status_code}",
                    "platform": "linkedin",
                }
        except Exception as e:
            logger.error(f"Failed to publish LinkedIn comment: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "platform": "linkedin",
            }

    # ====================
    # 统一发布接口
    # ====================

    async def publish_post(
        self,
        platform: str,
        content: str,
        title: Optional[str] = None,
        subreddit: Optional[str] = None,
    ) -> Dict[str, Any]:
        """统一发布帖子接口

        Args:
            platform: 平台 (reddit, twitter, linkedin)
            content: 帖子内容
            title: 标题（Reddit 必需）
            subreddit: Subreddit 名称（Reddit 必需）

        Returns:
            发布结果
        """
        if platform == "reddit":
            if not title or not subreddit:
                return {
                    "success": False,
                    "error": "Reddit requires title and subreddit",
                    "platform": "reddit",
                }
            return await self.publish_reddit_post(title, content, subreddit)
        elif platform == "twitter":
            return await self.publish_twitter_post(content)
        elif platform == "linkedin":
            return await self.publish_linkedin_post(content, title)
        else:
            return {
                "success": False,
                "error": f"Unsupported platform: {platform}",
            }

    async def publish_comment(
        self,
        platform: str,
        post_url: str,
        content: str,
        parent_comment_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """统一发布评论接口

        Args:
            platform: 平台 (reddit, twitter, linkedin)
            post_url: 目标帖子 URL
            content: 评论内容
            parent_comment_id: 父评论 ID（可选）

        Returns:
            发布结果
        """
        if platform == "reddit":
            return await self.publish_reddit_comment(post_url, content, parent_comment_id)
        elif platform == "twitter":
            return await self.publish_twitter_comment(post_url, content, parent_comment_id)
        elif platform == "linkedin":
            return await self.publish_linkedin_comment(post_url, content)
        else:
            return {
                "success": False,
                "error": f"Unsupported platform: {platform}",
            }


publisher_service = PublisherService()
