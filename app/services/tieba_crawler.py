"""Baidu Tieba (百度贴吧) Search Crawler Service.

A Playwright-based crawler for searching and extracting content from Tieba.
Uses the generic LoginManager for authentication.

Features:
- Search by keyword
- Multi-page pagination (up to 5 pages)
- Post content extraction
- First page comment extraction
- Clean formatted output
"""

import asyncio
import re
import time
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.auth.login_manager import Platform, get_login_manager

logger = get_logger(__name__)


@dataclass
class TiebaPost:
    """A single Tieba post from search results."""

    post_id: str
    title: str
    author: str
    author_id: Optional[str] = None
    content: str = ""
    forum_name: str = ""
    url: str = ""
    reply_count: int = 0
    created_at: Optional[str] = None
    last_reply_at: Optional[str] = None
    media_urls: List[str] = field(default_factory=list)
    is_thread: bool = True


@dataclass
class TiebaComment:
    """A comment on a Tieba post."""

    comment_id: str
    author: str
    author_id: Optional[str] = None
    content: str = ""
    floor: int = 0
    created_at: Optional[str] = None
    upvotes: int = 0


@dataclass
class TiebaPostDetail:
    """Detailed post with comments."""

    post: TiebaPost
    comments: List[TiebaComment] = field(default_factory=list)
    total_replies: int = 0


@dataclass
class TiebaSearchResult:
    """Result of a Tieba search operation."""

    keyword: str
    total_posts: int
    total_pages: int
    posts: List[TiebaPost]
    search_time: float
    error: Optional[str] = None


class TiebaCrawler:
    """Baidu Tieba search and content crawler.

    Usage:
        crawler = get_tieba_crawler()

        # Search for posts
        result = await crawler.search("关键词", pages=5)

        # Get post details with comments
        detail = await crawler.get_post_detail(post_url)

        # Clean and format for output
        formatted = crawler.format_result(result)
    """

    TIEBA_SEARCH_URL = "https://tieba.baidu.com/f/search/res"
    TIEBA_POST_URL = "https://tieba.baidu.com/p/{post_id}"
    DEFAULT_TIMEOUT = 30000
    DEFAULT_DELAY = 1.5

    def __init__(self, headless: bool = False):
        self.settings = get_settings()
        self.headless = headless
        self._login_manager = None

    @property
    def login_manager(self):
        if self._login_manager is None:
            self._login_manager = get_login_manager()
        return self._login_manager

    async def _ensure_context(self, require_login: bool = False):
        """Ensure we have a browser context for Tieba.

        Args:
            require_login: Whether to require logged-in context
        """
        if require_login:
            context, page = await self.login_manager.get_logged_in_context(
                Platform.TIEBA,
                headless=self.headless,
                auto_login=True,
            )
        else:
            context, page = await self.login_manager.get_context(
                Platform.TIEBA,
                headless=self.headless,
            )

        await self.login_manager.navigate_via_baidu(page)
        page = self.login_manager._pages.get(Platform.TIEBA, page)

        return context, page

    async def search(
        self,
        keyword: str,
        pages: int = 5,
        delay: Optional[float] = None,
        max_retries: int = 3,
    ) -> TiebaSearchResult:
        """Search Tieba for posts matching a keyword.

        Args:
            keyword: Search keyword
            pages: Number of pages to fetch (max 5)
            delay: Delay between page requests in seconds
            max_retries: Maximum retry attempts on failure

        Returns:
            TiebaSearchResult with posts
        """
        start_time = datetime.utcnow()
        delay = delay or self.DEFAULT_DELAY
        pages = min(pages, 5)

        all_posts: List[TiebaPost] = []

        for attempt in range(max_retries):
            try:
                # Require login for Tieba search to avoid anti-bot detection
                context, page = await self._ensure_context(require_login=True)

                for page_num in range(pages):
                    logger.info(f"Searching Tieba: '{keyword}' page {page_num + 1}/{pages}")

                    posts = await self._search_page_with_retry(page, keyword, page_num)

                    if posts is None:
                        logger.warning(
                            f"Captcha detected on page {page_num + 1}, waiting for resolution..."
                        )
                        if await self._handle_captcha(page):
                            posts = await self._search_page(page, keyword, page_num)
                        else:
                            raise RuntimeError("CAPTCHA not resolved")

                    if posts is None:
                        raise RuntimeError(f"Failed to get results after CAPTCHA handling")

                    all_posts.extend(posts)

                    if page_num < pages - 1:
                        await asyncio.sleep(delay)

                await self._save_cookies_after_operation()

                search_time = (datetime.utcnow() - start_time).total_seconds()

                return TiebaSearchResult(
                    keyword=keyword,
                    total_posts=len(all_posts),
                    total_pages=pages,
                    posts=all_posts,
                    search_time=search_time,
                )

            except Exception as e:
                logger.error(f"Tieba search failed (attempt {attempt + 1}/{max_retries}): {e}")

                if attempt < max_retries - 1:
                    logger.info("Retrying with fresh login...")
                    await self._force_relogin()
                    await asyncio.sleep(2)
                else:
                    search_time = (datetime.utcnow() - start_time).total_seconds()
                    return TiebaSearchResult(
                        keyword=keyword,
                        total_posts=0,
                        total_pages=0,
                        posts=[],
                        search_time=search_time,
                        error=str(e),
                    )

        search_time = (datetime.utcnow() - start_time).total_seconds()
        return TiebaSearchResult(
            keyword=keyword,
            total_posts=len(all_posts),
            total_pages=pages,
            posts=all_posts,
            search_time=search_time,
        )

    async def _search_page_with_retry(
        self,
        page,
        keyword: str,
        page_num: int,
    ) -> Optional[List[TiebaPost]]:
        """Fetch and parse a search result page with CAPTCHA detection."""
        encoded_keyword = urllib.parse.quote(keyword, safe="")
        pn = page_num * 10
        search_url = f"{self.TIEBA_SEARCH_URL}?qw={encoded_keyword}&pn={pn}&rn=10&un=&only_thread=1"

        await page.goto(search_url, wait_until="domcontentloaded", timeout=90000)
        await asyncio.sleep(2)

        current_url = page.url
        if "passport.baidu.com" in current_url or "login" in current_url.lower():
            logger.info("Detected login page, waiting for user login...")
            return None

        title = await page.title()
        if "安全验证" in title or "captcha" in page.url.lower():
            return None

        posts = await self._parse_search_results(page)
        return posts

    async def _handle_captcha(self, page) -> bool:
        """Handle CAPTCHA by waiting for user resolution."""
        try:
            title = await page.title()
            if "安全验证" not in title:
                return True

            logger.warning("CAPTCHA detected! Waiting for user to solve...")
            print("\n" + "=" * 60)
            print("⚠️  检测到验证码!")
            print("请在浏览器中完成验证...")
            print("=" * 60 + "\n")

            start_time = time.time()
            timeout = 180

            while time.time() - start_time < timeout:
                await asyncio.sleep(2)
                current_title = await page.title()
                if "安全验证" not in current_title:
                    logger.info("CAPTCHA resolved!")
                    return True

            logger.error("CAPTCHA resolution timeout")
            return False

        except Exception as e:
            logger.error(f"Error handling CAPTCHA: {e}")
            return False

    async def _force_relogin(self):
        """Force re-login by clearing state."""
        try:
            await self.login_manager.logout(Platform.TIEBA)
            logger.info("Cleared login state, will require fresh login")
        except Exception as e:
            logger.warning(f"Failed to clear login state: {e}")

    async def _save_cookies_after_operation(self):
        """Save cookies after completing an operation."""
        try:
            if Platform.TIEBA in self.login_manager._contexts:
                context = self.login_manager._contexts[Platform.TIEBA]
                await self.login_manager._save_cookies(Platform.TIEBA, context)
                logger.debug("Saved cookies after operation")
        except Exception as e:
            logger.warning(f"Failed to save cookies: {e}")

    async def _search_page(
        self,
        page,
        keyword: str,
        page_num: int,
    ) -> List[TiebaPost]:
        """Fetch and parse a single search result page."""
        encoded_keyword = urllib.parse.quote(keyword)
        pn = page_num * 10
        search_url = f"{self.TIEBA_SEARCH_URL}?qw={encoded_keyword}&pn={pn}&rn=10&un=&only_thread=1"

        await page.goto(search_url, wait_until="networkidle")
        await asyncio.sleep(1)

        posts = await self._parse_search_results(page)
        return posts

    async def _parse_search_results(self, page) -> List[TiebaPost]:
        """Parse search results from the current page."""
        posts = []

        try:
            result_items = await page.query_selector_all(".s_post")

            if not result_items:
                result_items = await page.query_selector_all(".p_title")

            if not result_items:
                result_items = await page.query_selector_all('[class*="result"]')

            for item in result_items:
                try:
                    post = await self._parse_search_item(item)
                    if post:
                        posts.append(post)
                except Exception as e:
                    logger.debug(f"Failed to parse search item: {e}")
                    continue

        except Exception as e:
            logger.error(f"Failed to parse search results: {e}")

        return posts

    async def _parse_search_item(self, item) -> Optional[TiebaPost]:
        """Parse a single search result item."""
        try:
            title_elem = await item.query_selector(".p_title a, .title a, a[class*='title']")
            if not title_elem:
                title_elem = await item.query_selector("a[href*='/p/']")

            if not title_elem:
                return None

            title = await title_elem.text_content()
            title = title.strip() if title else ""

            href = await title_elem.get_attribute("href")
            post_id = self._extract_post_id(href) if href else None

            if not post_id:
                return None

            author = "未知"
            author_elem = await item.query_selector(".p_author_name, .author a, [class*='author']")
            if author_elem:
                author_text = await author_elem.text_content()
                author = author_text.strip() if author_text else "未知"

            forum_name = ""
            forum_elem = await item.query_selector(".p_forum a, .forum a, [class*='forum']")
            if forum_elem:
                forum_name = await forum_elem.text_content()
                forum_name = forum_name.strip() if forum_name else ""

            content = ""
            content_elem = await item.query_selector(".p_content, .content, [class*='content']")
            if content_elem:
                content = await content_elem.text_content()
                content = content.strip() if content else ""

            reply_count = 0
            reply_elem = await item.query_selector(".p_reply, .reply, [class*='reply']")
            if reply_elem:
                reply_text = await reply_elem.text_content()
                if reply_text:
                    match = re.search(r"(\d+)", reply_text)
                    if match:
                        reply_count = int(match.group(1))

            url = f"https://tieba.baidu.com/p/{post_id}"

            return TiebaPost(
                post_id=post_id,
                title=title,
                author=author,
                content=content,
                forum_name=forum_name,
                url=url,
                reply_count=reply_count,
                is_thread=True,
            )

        except Exception as e:
            logger.debug(f"Error parsing search item: {e}")
            return None

    def _extract_post_id(self, href: str) -> Optional[str]:
        """Extract post ID from a URL."""
        if not href:
            return None

        match = re.search(r"/p/(\d+)", href)
        if match:
            return match.group(1)

        match = re.search(r"tid=(\d+)", href)
        if match:
            return match.group(1)

        return None

    async def get_post_detail(
        self,
        post_url: str,
        max_comments: int = 30,
    ) -> Optional[TiebaPostDetail]:
        """Get detailed post content with comments.

        Args:
            post_url: URL of the post
            max_comments: Maximum number of comments to extract

        Returns:
            TiebaPostDetail with post and comments
        """
        try:
            context, page = await self._ensure_context(require_login=False)

            post_id = self._extract_post_id(post_url)
            if not post_id:
                post_id = post_url

            full_url = f"https://tieba.baidu.com/p/{post_id}"

            await page.goto(full_url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(2)

            post = await self._parse_post_content(page, post_id)
            comments = await self._parse_comments(page, max_comments)

            return TiebaPostDetail(
                post=post,
                comments=comments,
                total_replies=post.reply_count,
            )

        except Exception as e:
            logger.error(f"Failed to get post detail: {e}")
            return None

    async def _parse_post_content(self, page, post_id: str) -> TiebaPost:
        """Parse the main post content."""
        title = ""
        title_elem = await page.query_selector(".core_title_txt, h1.title, .thread_title")
        if title_elem:
            title = await title_elem.text_content()
            title = title.strip() if title else ""

        author = "未知"
        author_elem = await page.query_selector(
            ".d_name a, .louzhubiaoshi_wrap a, [class*='author']"
        )
        if author_elem:
            author = await author_elem.text_content()
            author = author.strip() if author else "未知"

        author_id = None
        author_link = await page.query_selector('.d_name a[href*="un="]')
        if author_link:
            href = await author_link.get_attribute("href")
            if href:
                match = re.search(r"un=([^&]+)", href)
                if match:
                    author_id = urllib.parse.unquote(match.group(1))

        content = ""
        content_elem = await page.query_selector(
            ".d_post_content, .j_d_post_content, [class*='post_content']"
        )
        if content_elem:
            content = await content_elem.inner_text()
            content = content.strip() if content else ""

        reply_count = 0
        reply_elem = await page.query_selector(".l_reply_num, .thread_reply_num, [class*='reply']")
        if reply_elem:
            reply_text = await reply_elem.text_content()
            if reply_text:
                match = re.search(r"(\d+)", reply_text)
                if match:
                    reply_count = int(match.group(1))

        forum_name = ""
        forum_elem = await page.query_selector(".card_title, .nav_right a, [class*='forum']")
        if forum_elem:
            forum_name = await forum_elem.text_content()
            forum_name = forum_name.strip() if forum_name else ""

        media_urls: List[str] = []
        img_elements = await page.query_selector_all(
            '.d_post_content img, .j_d_post_content img, [class*="content"] img'
        )
        for img in img_elements[:5]:
            src = await img.get_attribute("src")
            if src and src.startswith("http"):
                media_urls.append(src)

        return TiebaPost(
            post_id=post_id,
            title=title,
            author=author,
            author_id=author_id,
            content=content,
            forum_name=forum_name,
            url=f"https://tieba.baidu.com/p/{post_id}",
            reply_count=reply_count,
            media_urls=media_urls,
            is_thread=True,
        )

    async def _parse_comments(self, page, max_comments: int) -> List[TiebaComment]:
        """Parse comments from the first page of replies."""
        comments: List[TiebaComment] = []

        try:
            comment_items = await page.query_selector_all(
                '.j_lzl_m_w, .l_post[data-field], [class*="reply_item"]'
            )

            if not comment_items:
                comment_items = await page.query_selector_all(".l_post")

            count = 0
            for item in comment_items:
                if count >= max_comments:
                    break

                comment = await self._parse_comment_item(item, count + 1)
                if comment:
                    comments.append(comment)
                    count += 1

        except Exception as e:
            logger.error(f"Failed to parse comments: {e}")

        return comments

    async def _parse_comment_item(self, item, floor: int) -> Optional[TiebaComment]:
        """Parse a single comment item."""
        try:
            author = "未知"
            author_elem = await item.query_selector(
                ".d_name a, .louzhubiaoshi_wrap a, [class*='author']"
            )
            if author_elem:
                author = await author_elem.text_content()
                author = author.strip() if author else "未知"

            author_id = None
            author_link = await item.query_selector('a[href*="un="]')
            if author_link:
                href = await author_link.get_attribute("href")
                if href:
                    match = re.search(r"un=([^&]+)", href)
                    if match:
                        author_id = urllib.parse.unquote(match.group(1))

            content = ""
            content_elem = await item.query_selector(
                ".d_post_content, .j_d_post_content, [class*='content']"
            )
            if content_elem:
                content = await content_elem.inner_text()
                content = content.strip() if content else ""

            comment_id = f"floor_{floor}"

            upvotes = 0
            upvote_elem = await item.query_selector(".p_tail .p_tail_last, [class*='like']")
            if upvote_elem:
                upvote_text = await upvote_elem.text_content()
                if upvote_text:
                    match = re.search(r"(\d+)", upvote_text)
                    if match:
                        upvotes = int(match.group(1))

            return TiebaComment(
                comment_id=comment_id,
                author=author,
                author_id=author_id,
                content=content,
                floor=floor,
                upvotes=upvotes,
            )

        except Exception as e:
            logger.debug(f"Failed to parse comment: {e}")
            return None

    def format_result(self, result: TiebaSearchResult) -> Dict[str, Any]:
        """Format search result for API response.

        Args:
            result: TiebaSearchResult to format

        Returns:
            Dict with clean formatted data
        """
        if result.error:
            return {
                "success": False,
                "error": result.error,
                "keyword": result.keyword,
            }

        posts_data = []
        for post in result.posts:
            posts_data.append(
                {
                    "post_id": post.post_id,
                    "title": self._clean_text(post.title),
                    "author": post.author,
                    "author_id": post.author_id,
                    "content": self._clean_text(post.content),
                    "forum_name": post.forum_name,
                    "url": post.url,
                    "reply_count": post.reply_count,
                    "created_at": post.created_at,
                    "media_urls": post.media_urls,
                }
            )

        return {
            "success": True,
            "keyword": result.keyword,
            "total_posts": result.total_posts,
            "total_pages": result.total_pages,
            "search_time": round(result.search_time, 2),
            "posts": posts_data,
        }

    def format_post_detail(self, detail: TiebaPostDetail) -> Dict[str, Any]:
        """Format post detail for API response.

        Args:
            detail: TiebaPostDetail to format

        Returns:
            Dict with clean formatted data
        """
        if not detail:
            return {"success": False, "error": "Post not found"}

        comments_data = []
        for comment in detail.comments:
            comments_data.append(
                {
                    "comment_id": comment.comment_id,
                    "author": comment.author,
                    "author_id": comment.author_id,
                    "content": self._clean_text(comment.content),
                    "floor": comment.floor,
                    "upvotes": comment.upvotes,
                }
            )

        return {
            "success": True,
            "post": {
                "post_id": detail.post.post_id,
                "title": self._clean_text(detail.post.title),
                "author": detail.post.author,
                "author_id": detail.post.author_id,
                "content": self._clean_text(detail.post.content),
                "forum_name": detail.post.forum_name,
                "url": detail.post.url,
                "reply_count": detail.post.reply_count,
                "media_urls": detail.post.media_urls,
            },
            "comments": comments_data,
            "total_replies": detail.total_replies,
        }

    def _clean_text(self, text: str) -> str:
        """Clean text content for output."""
        if not text:
            return ""

        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"收起|展开|更多\s*|查看全部", "", text)
        text = text.strip()

        return text


_tieba_crawler_instance: Optional[TiebaCrawler] = None


def get_tieba_crawler(headless: Optional[bool] = None) -> TiebaCrawler:
    """Get the singleton TiebaCrawler instance.

    Args:
        headless: Whether to run browser in headless mode.
                 If None, uses system-wide playwright_headless setting from config.
    """
    global _tieba_crawler_instance
    if _tieba_crawler_instance is None:
        settings = get_settings()
        # Use system-wide setting if headless not explicitly provided
        if headless is None:
            headless = settings.playwright_headless
        _tieba_crawler_instance = TiebaCrawler(headless=headless)
    return _tieba_crawler_instance
