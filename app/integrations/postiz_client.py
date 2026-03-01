"""Postiz API client for publishing to social media platforms.

Postiz provides a unified API for posting to 32+ social media platforms.
This client handles:
  - Reddit text and link posts
  - Twitter/X posts and threads
  - Other social media platforms as needed
"""

import httpx
import json
from typing import Optional, Dict, List, Any
from datetime import datetime
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class PostizClient:
    """Client for Postiz Public API."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """Initialize Postiz client.

        Args:
            api_key: Postiz API key. Defaults to POSTIZ_API_KEY from settings.
            base_url: Postiz API base URL. Defaults to Postiz Cloud.
        """
        settings = get_settings()
        self.api_key = api_key or settings.postiz_api_key
        self.base_url = base_url or "https://api.postiz.com/public/v1"

        if not self.api_key:
            logger.warning("POSTIZ_API_KEY not set - Postiz integration will not work")

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        return {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
        }

    async def post_to_reddit(
        self,
        integration_id: str,
        content: str,
        subreddit: str,
        title: str,
        post_type: str = "self",
        url: Optional[str] = None,
        schedule_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Post content to Reddit.

        Args:
            integration_id: Postiz Reddit integration ID
            content: Post content (text for self posts)
            subreddit: Subreddit name (without r/)
            title: Post title
            post_type: Post type - "self" (default) or "link"
            url: URL for link posts
            schedule_at: ISO datetime to schedule post (default: post now)

        Returns:
            {
                "success": bool,
                "post_id": str (if successful),
                "scheduled_for": str (if scheduled),
                "error": str (if failed),
                "response": dict (full API response)
            }
        """
        try:
            logger.info(f"Posting to Reddit: r/{subreddit} - {title}")

            if not self.api_key:
                return {"success": False, "error": "Postiz API key not configured"}

            # Determine post type and validate
            if post_type not in ["self", "link", "image", "video"]:
                post_type = "self"

            if post_type == "link" and not url:
                return {"success": False, "error": "URL required for link posts"}

            # Build subreddit settings
            subreddit_value = {
                "subreddit": subreddit,
                "title": title,
                "type": post_type,
                "url": url or "",
                "is_flair_required": False,
                "flair": None,
            }

            # Build request payload
            payload = {
                "type": "schedule" if schedule_at else "now",
                "date": schedule_at or datetime.utcnow().isoformat() + "Z",
                "shortLink": False,
                "tags": [],
                "posts": [
                    {
                        "integration": {"id": integration_id},
                        "value": [{"content": content, "image": []}],
                        "settings": {"__type": "reddit", "subreddit": [{"value": subreddit_value}]},
                    }
                ],
            }

            # Make request
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/posts", json=payload, headers=self._get_headers()
                )

            if response.status_code in [200, 201]:
                result = response.json()
                logger.info(f"Successfully posted to Reddit: {result}")

                return {
                    "success": True,
                    "post_id": result.get("id"),
                    "scheduled_for": schedule_at,
                    "response": result,
                }
            else:
                error_msg = f"Postiz API error: {response.status_code} - {response.text}"
                logger.error(error_msg)

                return {
                    "success": False,
                    "error": error_msg,
                    "response": response.json() if response.text else {},
                }

        except Exception as e:
            error_msg = f"Failed to post to Reddit: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    async def post_to_twitter(
        self,
        integration_id: str,
        content: str,
        who_can_reply: str = "everyone",
        thread_content: Optional[List[str]] = None,
        schedule_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Post content to Twitter/X.

        Args:
            integration_id: Postiz X integration ID
            content: Tweet content (first tweet if thread)
            who_can_reply: Who can reply - "everyone", "following", "mentionedUsers", "subscribers", "verified"
            thread_content: Additional tweets for thread (optional)
            schedule_at: ISO datetime to schedule post (default: post now)

        Returns:
            {
                "success": bool,
                "post_id": str (if successful),
                "scheduled_for": str (if scheduled),
                "error": str (if failed),
                "response": dict (full API response)
            }
        """
        try:
            logger.info(f"Posting to Twitter/X")

            if not self.api_key:
                return {"success": False, "error": "Postiz API key not configured"}

            # Validate who_can_reply value
            valid_reply_options = [
                "everyone",
                "following",
                "mentionedUsers",
                "subscribers",
                "verified",
            ]
            if who_can_reply not in valid_reply_options:
                who_can_reply = "everyone"

            # Build tweet values (for thread support)
            tweets = [{"content": content, "image": []}]

            if thread_content:
                for tweet in thread_content:
                    tweets.append({"content": tweet, "image": []})

            # Build request payload
            payload = {
                "type": "schedule" if schedule_at else "now",
                "date": schedule_at or datetime.utcnow().isoformat() + "Z",
                "shortLink": False,
                "tags": [],
                "posts": [
                    {
                        "integration": {"id": integration_id},
                        "value": tweets,
                        "settings": {
                            "__type": "x",
                            "who_can_reply_post": who_can_reply,
                            "community": "",
                        },
                    }
                ],
            }

            # Make request
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/posts", json=payload, headers=self._get_headers()
                )

            if response.status_code in [200, 201]:
                result = response.json()
                logger.info(f"Successfully posted to Twitter/X: {result}")

                return {
                    "success": True,
                    "post_id": result.get("id"),
                    "scheduled_for": schedule_at,
                    "response": result,
                }
            else:
                error_msg = f"Postiz API error: {response.status_code} - {response.text}"
                logger.error(error_msg)

                return {
                    "success": False,
                    "error": error_msg,
                    "response": response.json() if response.text else {},
                }

        except Exception as e:
            error_msg = f"Failed to post to Twitter/X: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    async def get_integrations(self) -> Dict[str, Any]:
        """Get list of available integrations (connected social accounts).

        Returns:
            {
                "success": bool,
                "integrations": [
                    {
                        "id": str,
                        "provider": str,
                        "name": str
                    }
                ],
                "error": str (if failed)
            }
        """
        try:
            logger.info("Fetching Postiz integrations")

            if not self.api_key:
                return {"success": False, "error": "Postiz API key not configured"}

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/integrations", headers=self._get_headers()
                )

            if response.status_code == 200:
                result = response.json()
                logger.info(f"Found {len(result.get('integrations', []))} integrations")

                return {"success": True, "integrations": result.get("integrations", [])}
            else:
                error_msg = f"Postiz API error: {response.status_code} - {response.text}"
                logger.error(error_msg)

                return {"success": False, "error": error_msg}

        except Exception as e:
            error_msg = f"Failed to get integrations: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}


# Singleton instance
_postiz_client: Optional[PostizClient] = None


def get_postiz_client() -> PostizClient:
    """Get or create Postiz client instance."""
    global _postiz_client
    if _postiz_client is None:
        _postiz_client = PostizClient()
    return _postiz_client
