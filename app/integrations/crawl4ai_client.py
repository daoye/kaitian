"""Crawl4AI HTTP API client for web scraping with AI-powered extraction."""

from typing import Optional, Dict, Any
import httpx
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class Crawl4AIClient:
    """Client for Crawl4AI HTTP API."""

    def __init__(self, api_url: Optional[str] = None, timeout: int = 30):
        """Initialize Crawl4AI API client.

        Args:
            api_url: Crawl4AI API base URL. Defaults to CRAWL4AI_API_URL from settings.
            timeout: Request timeout in seconds.
        """
        settings = get_settings()
        self.api_url = api_url or settings.crawl4ai_api_url or "http://localhost:8001"
        self.timeout = timeout
        self.enabled = settings.crawl4ai_enabled

        if not self.enabled:
            logger.warning("Crawl4AI is disabled via configuration")

    async def crawl(
        self,
        url: str,
        extraction_schema: Optional[Dict[str, Any]] = None,
        wait_for_selector: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Crawl a URL using Crawl4AI API.

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
            - status_code: int
            - error: str (if failed)
        """
        if not self.enabled:
            return {"success": False, "error": "Crawl4AI is disabled", "url": url}

        try:
            logger.info(f"Calling Crawl4AI API for URL: {url}")

            payload = {
                "url": url,
                "wait_for_selector": wait_for_selector,
                "extraction_schema": extraction_schema,
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.api_url}/crawl",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )

            if response.status_code == 200:
                result = response.json()
                logger.info(f"Crawl4AI crawl completed successfully for {url}")
                return result
            else:
                error_msg = f"Crawl4AI API error {response.status_code}: {response.text}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "url": url,
                    "status_code": response.status_code,
                }

        except httpx.TimeoutException:
            error_msg = f"Crawl4AI API timeout after {self.timeout}s for {url}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg, "url": url}
        except Exception as e:
            error_msg = f"Crawl4AI API call failed for {url}: {str(e)}"
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
        logger.info(f"Starting concurrent crawl for {len(urls)} URLs via API")

        tasks = [self.crawl(url, **kwargs) for url in urls]

        import asyncio

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
