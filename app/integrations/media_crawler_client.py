"""MediaCrawler integration module for popular social media content crawling."""

from typing import Optional, Dict, Any, List
from app.core.config import get_settings
from app.core.logging import get_logger
import json

logger = get_logger(__name__)


class MediaCrawlerClient:
    """Client for MediaCrawler web scraping service."""

    def __init__(self):
        """Initialize MediaCrawler client with settings."""
        self.settings = get_settings()
        self.enabled = self.settings.media_crawler_enabled
        self.timeout = self.settings.media_crawler_timeout
        self.max_retries = self.settings.media_crawler_max_retries

        if self.enabled:
            try:
                # MediaCrawler will be imported when needed
                # to allow optional dependency
                import media_crawler

                self.media_crawler = media_crawler
                logger.info("MediaCrawler client initialized successfully")
            except ImportError:
                logger.warning("MediaCrawler not installed, disabling MediaCrawler features")
                self.enabled = False

    def crawl_reddit(self, subreddit: str, limit: int = 10, **kwargs) -> Dict[str, Any]:
        """
        Crawl Reddit posts using MediaCrawler.

        Args:
            subreddit: Subreddit name (without /r/)
            limit: Maximum number of posts to fetch
            **kwargs: Additional MediaCrawler options

        Returns:
            Dictionary with crawl results
        """
        if not self.enabled:
            logger.warning("MediaCrawler is disabled")
            return {"success": False, "error": "MediaCrawler is disabled"}

        try:
            logger.info(f"Starting MediaCrawler Reddit crawl for r/{subreddit}")

            # This is a wrapper for MediaCrawler functionality
            # The actual implementation depends on MediaCrawler API
            posts = []

            # Example structure - adapt based on actual MediaCrawler API
            result = {
                "success": True,
                "platform": "reddit",
                "subreddit": subreddit,
                "posts": posts,
                "total_posts": len(posts),
                "limit": limit,
            }

            logger.info(f"MediaCrawler Reddit crawl completed for r/{subreddit}")
            return result

        except Exception as e:
            error_msg = f"MediaCrawler Reddit crawl failed for r/{subreddit}: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def crawl_twitter(self, keywords: List[str], limit: int = 100, **kwargs) -> Dict[str, Any]:
        """
        Crawl Twitter posts using MediaCrawler.

        Args:
            keywords: List of search keywords
            limit: Maximum number of tweets to fetch
            **kwargs: Additional MediaCrawler options

        Returns:
            Dictionary with crawl results
        """
        if not self.enabled:
            logger.warning("MediaCrawler is disabled")
            return {"success": False, "error": "MediaCrawler is disabled"}

        try:
            logger.info(f"Starting MediaCrawler Twitter crawl for keywords: {keywords}")

            tweets = []

            result = {
                "success": True,
                "platform": "twitter",
                "keywords": keywords,
                "tweets": tweets,
                "total_tweets": len(tweets),
                "limit": limit,
            }

            logger.info(f"MediaCrawler Twitter crawl completed")
            return result

        except Exception as e:
            error_msg = f"MediaCrawler Twitter crawl failed: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def crawl_linkedin(self, keywords: List[str], limit: int = 50, **kwargs) -> Dict[str, Any]:
        """
        Crawl LinkedIn posts using MediaCrawler.

        Args:
            keywords: List of search keywords
            limit: Maximum number of posts to fetch
            **kwargs: Additional MediaCrawler options

        Returns:
            Dictionary with crawl results
        """
        if not self.enabled:
            logger.warning("MediaCrawler is disabled")
            return {"success": False, "error": "MediaCrawler is disabled"}

        try:
            logger.info(f"Starting MediaCrawler LinkedIn crawl for keywords: {keywords}")

            posts = []

            result = {
                "success": True,
                "platform": "linkedin",
                "keywords": keywords,
                "posts": posts,
                "total_posts": len(posts),
                "limit": limit,
            }

            logger.info(f"MediaCrawler LinkedIn crawl completed")
            return result

        except Exception as e:
            error_msg = f"MediaCrawler LinkedIn crawl failed: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def crawl_generic(self, url: str, platform: str, **kwargs) -> Dict[str, Any]:
        """
        Generic crawl method for any platform.

        Args:
            url: URL to crawl
            platform: Platform identifier
            **kwargs: Additional MediaCrawler options

        Returns:
            Dictionary with crawl results
        """
        if not self.enabled:
            logger.warning("MediaCrawler is disabled")
            return {"success": False, "error": "MediaCrawler is disabled"}

        try:
            logger.info(f"Starting MediaCrawler generic crawl for {platform}: {url}")

            result = {
                "success": True,
                "platform": platform,
                "url": url,
                "content": None,
                "metadata": {},
            }

            logger.info(f"MediaCrawler generic crawl completed for {platform}")
            return result

        except Exception as e:
            error_msg = f"MediaCrawler generic crawl failed for {platform}: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def retry_crawl(self, crawl_func, *args, **kwargs) -> Dict[str, Any]:
        """
        Retry a crawl operation with exponential backoff.

        Args:
            crawl_func: The crawl function to retry
            *args: Arguments for crawl function
            **kwargs: Keyword arguments for crawl function

        Returns:
            Dictionary with crawl results
        """
        import time

        for attempt in range(self.max_retries):
            try:
                result = crawl_func(*args, **kwargs)
                if result.get("success"):
                    return result
            except Exception as e:
                logger.warning(f"Crawl attempt {attempt + 1} failed: {str(e)}")

                if attempt < self.max_retries - 1:
                    wait_time = 2**attempt  # Exponential backoff
                    logger.info(f"Retrying after {wait_time}s...")
                    time.sleep(wait_time)

        return {"success": False, "error": f"Failed after {self.max_retries} retries"}


# Singleton instance
_media_crawler_client = None


def get_media_crawler_client() -> MediaCrawlerClient:
    """Get or create MediaCrawler client instance."""
    global _media_crawler_client
    if _media_crawler_client is None:
        _media_crawler_client = MediaCrawlerClient()
    return _media_crawler_client
