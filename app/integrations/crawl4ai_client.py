"""Crawl4AI integration module for web scraping with AI-powered extraction."""

from typing import Optional, Dict, Any
import asyncio
from app.core.config import get_settings
from app.core.logging import get_logger
import json

logger = get_logger(__name__)


class Crawl4AIClient:
    """Client for Crawl4AI web scraping service."""

    def __init__(self):
        """Initialize Crawl4AI client with settings."""
        self.settings = get_settings()
        self.enabled = self.settings.crawl4ai_enabled
        self.timeout = self.settings.crawl4ai_timeout
        self.browser_type = self.settings.crawl4ai_browser_type

        if self.enabled:
            try:
                from crawl4ai import AsyncWebCrawler

                self.AsyncWebCrawler = AsyncWebCrawler
                logger.info("Crawl4AI client initialized successfully")
            except ImportError:
                logger.warning("Crawl4AI not installed, disabling Crawl4AI features")
                self.enabled = False

    async def crawl(
        self,
        url: str,
        extraction_schema: Optional[Dict[str, Any]] = None,
        wait_for_selector: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Crawl a URL using Crawl4AI.

        Args:
            url: Target URL to crawl
            extraction_schema: Optional schema for data extraction
            wait_for_selector: CSS selector to wait for before extraction

        Returns:
            Dictionary with crawl results containing:
            - success: bool
            - content: str (markdown formatted)
            - raw_html: str
            - extracted_data: dict
            - error: str (if failed)
        """
        if not self.enabled:
            logger.warning("Crawl4AI is disabled")
            return {"success": False, "error": "Crawl4AI is disabled"}

        try:
            logger.info(f"Starting Crawl4AI crawl for URL: {url}")

            async with self.AsyncWebCrawler(
                browser_type=self.browser_type, timeout=self.timeout
            ) as crawler:
                result = await crawler.arun(
                    url=url,
                    wait_for_selector=wait_for_selector,
                    extraction_schema=extraction_schema,
                )

                crawl_result = {
                    "success": result.success,
                    "url": url,
                    "content": result.markdown,
                    "raw_html": result.html,
                    "extracted_data": result.extracted_content,
                    "status_code": result.status_code,
                }

                logger.info(f"Crawl4AI crawl completed successfully for {url}")
                return crawl_result

        except asyncio.TimeoutError:
            error_msg = f"Crawl4AI timeout after {self.timeout}s for {url}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg, "url": url}
        except Exception as e:
            error_msg = f"Crawl4AI crawl failed for {url}: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg, "url": url}

    async def crawl_with_extraction(
        self,
        url: str,
        extraction_fields: Dict[str, str],
    ) -> Dict[str, Any]:
        """
        Crawl a URL and extract specific fields.

        Args:
            url: Target URL
            extraction_fields: Dictionary mapping field names to CSS selectors

        Returns:
            Dictionary with extracted data
        """
        schema = {
            "type": "object",
            "properties": {
                field: {"type": "string", "selector": selector}
                for field, selector in extraction_fields.items()
            },
        }

        return await self.crawl(url, extraction_schema=schema)

    async def crawl_multiple(self, urls: list[str], **kwargs) -> list[Dict[str, Any]]:
        """
        Crawl multiple URLs concurrently.

        Args:
            urls: List of URLs to crawl
            **kwargs: Additional arguments to pass to crawl()

        Returns:
            List of crawl results
        """
        logger.info(f"Starting concurrent crawl for {len(urls)} URLs")

        tasks = [self.crawl(url, **kwargs) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        crawl_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                crawl_results.append({"success": False, "error": str(result), "url": urls[i]})
            else:
                crawl_results.append(result)

        logger.info(f"Completed concurrent crawl for {len(urls)} URLs")
        return crawl_results

    @staticmethod
    def parse_crawled_content(content: str, keywords: list[str]) -> Dict[str, Any]:
        """
        Parse crawled markdown content for keywords.

        Args:
            content: Markdown formatted content
            keywords: List of keywords to search for

        Returns:
            Dictionary with parsed results
        """
        results = {
            "found_keywords": [],
            "keyword_positions": {},
            "content_length": len(content),
            "keyword_count": 0,
        }

        content_lower = content.lower()

        for keyword in keywords:
            keyword_lower = keyword.lower()
            count = content_lower.count(keyword_lower)

            if count > 0:
                results["found_keywords"].append(keyword)
                results["keyword_count"] += count
                results["keyword_positions"][keyword] = count

        return results


# Singleton instance
_crawl4ai_client = None


def get_crawl4ai_client() -> Crawl4AIClient:
    """Get or create Crawl4AI client instance."""
    global _crawl4ai_client
    if _crawl4ai_client is None:
        _crawl4ai_client = Crawl4AIClient()
    return _crawl4ai_client
