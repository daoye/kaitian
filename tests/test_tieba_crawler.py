"""Tieba Crawler Test and Usage Guide

This script demonstrates how to use the Tieba crawler with proper error handling
and CAPTCHA workaround.

Usage:
    uv run python tests/test_tieba_crawler.py

Notes:
    - First time use requires manual CAPTCHA solving
    - Login state is persisted in cookies for subsequent uses
    - Search works without login but may trigger CAPTCHA
"""

import asyncio
import sys
from app.services.tieba_crawler import get_tieba_crawler
from app.services.auth.login_manager import Platform, get_login_manager


async def test_login_flow():
    """Test the manual login flow for first-time setup."""
    print("=" * 60)
    print("Tieba Crawler - First Time Setup")
    print("=" * 60)
    print("\nThis will open a browser window for you to complete CAPTCHA/login.")
    print("Please complete any verification shown in the browser.\n")

    lm = get_login_manager()

    try:
        # Get context (will open browser)
        print("Opening browser...")
        context, page = await lm.get_context(Platform.TIEBA, headless=False)

        # Navigate to Tieba
        print("Navigating to Tieba...")
        await page.goto("https://tieba.baidu.com", wait_until="networkidle")

        print(f"\nCurrent URL: {page.url}")
        print(f"Page Title: {await page.title()}")

        # Check if we need to solve CAPTCHA
        if "安全验证" in await page.title() or "captcha" in page.url.lower():
            print("\n⚠️  CAPTCHA detected! Please solve it manually in the browser.")
            print("   Waiting 30 seconds for you to complete verification...")
            await asyncio.sleep(30)

        # Check login status
        is_logged = await lm.is_logged_in(Platform.TIEBA)
        print(f"\n✓ Login status: {'Logged in' if is_logged else 'Not logged in'}")

        if is_logged:
            print("✓ Cookies saved for future use")

        await lm.close()
        print("\n✓ Setup completed")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback

        traceback.print_exc()


async def test_search():
    """Test search functionality."""
    print("\n" + "=" * 60)
    print("Testing Search Functionality")
    print("=" * 60)

    crawler = get_tieba_crawler()

    try:
        # Search for Python-related posts
        print("\nSearching for 'Python'...")
        result = await crawler.search(keyword="Python", pages=1, delay=2.0)

        print(f"\n✓ Search completed in {result.search_time:.2f}s")
        print(f"  Total posts found: {result.total_posts}")

        if result.error:
            print(f"  ⚠️  Error: {result.error}")

        if result.posts:
            print(f"\n  Top 3 results:")
            for i, post in enumerate(result.posts[:3], 1):
                print(f"\n  {i}. {post.title}")
                print(f"     Author: {post.author} | Forum: {post.forum_name}")
                print(f"     Replies: {post.reply_count} | URL: {post.url}")
        else:
            print("\n  ⚠️  No posts found. This may indicate:")
            print("     - CAPTCHA blocking the request")
            print("     - The search selectors need updating")
            print("     - Network connectivity issues")

        await crawler.login_manager.close()

    except Exception as e:
        print(f"\n✗ Search failed: {e}")
        import traceback

        traceback.print_exc()


async def test_post_detail():
    """Test post detail extraction."""
    print("\n" + "=" * 60)
    print("Testing Post Detail Extraction")
    print("=" * 60)

    crawler = get_tieba_crawler()

    # Use a sample post URL (you can replace with any valid Tieba post URL)
    test_url = "https://tieba.baidu.com/p/123456"  # Replace with real URL

    try:
        print(f"\nFetching post detail: {test_url}")
        detail = await crawler.get_post_detail(post_url=test_url, max_comments=5)

        if detail:
            print(f"\n✓ Post found:")
            print(f"  Title: {detail.post.title}")
            print(f"  Author: {detail.post.author}")
            print(f"  Content: {detail.post.content[:200]}...")
            print(f"  Total replies: {detail.total_replies}")

            if detail.comments:
                print(f"\n  First {len(detail.comments)} comments:")
                for comment in detail.comments[:3]:
                    print(f"    - {comment.author}: {comment.content[:50]}...")
        else:
            print("\n⚠️  Post not found")

        await crawler.login_manager.close()

    except Exception as e:
        print(f"\n✗ Failed to get post detail: {e}")


def print_usage_guide():
    """Print usage guide."""
    print("\n" + "=" * 60)
    print("Usage Guide")
    print("=" * 60)
    print("""
1. First Time Setup:
   - Run this script to complete initial CAPTCHA/login
   - Cookies will be saved for future use
   - Subsequent runs won't require manual interaction

2. API Usage:
   ```python
   from app.services.tieba_crawler import get_tieba_crawler
   
   crawler = get_tieba_crawler()
   result = await crawler.search(keyword="Python", pages=5)
   formatted = crawler.format_result(result)
   ```

3. HTTP API:
   ```bash
   # Search
   curl -X POST "http://localhost:8000/api/v1/crawler/tieba/search?keyword=Python&pages=5"
   
   # Get post detail
   curl -X POST "http://localhost:8000/api/v1/crawler/tieba/post?post_url=<URL>"
   ```

4. Known Limitations:
   - CAPTCHA may appear on first use or after inactivity
   - Search results depend on Tieba's anti-bot measures
   - Rate limiting applies (use delay parameter)
""")


async def main():
    """Main test function."""
    if len(sys.argv) > 1 and sys.argv[1] == "--setup":
        await test_login_flow()
    else:
        print("Tieba Crawler Test Suite")
        print("Run with --setup flag for first-time setup")
        print()

        # Run tests
        await test_search()
        await test_post_detail()
        print_usage_guide()


if __name__ == "__main__":
    asyncio.run(main())
