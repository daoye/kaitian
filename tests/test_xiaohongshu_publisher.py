#!/usr/bin/env python3
"""Test script for Xiaohongshu Playwright Publisher

Usage:
    python test_xiaohongshu_publisher.py --login    # Wait for login only
    python test_xiaohongshu_publisher.py --test     # Full test with sample images
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.xiaohongshu_publisher import XiaohongshuPlaywrightPublisher


async def test_login():
    """Test login functionality."""
    print("=" * 60)
    print("Testing Xiaohongshu Login")
    print("=" * 60)

    publisher = XiaohongshuPlaywrightPublisher(headless=False)

    try:
        await publisher._ensure_context()

        if await publisher._check_login_status():
            print("✓ Already logged in!")
            return True

        print("Waiting for login...")
        if await publisher.wait_for_login():
            print("✓ Login successful!")
            return True
        else:
            print("✗ Login failed or timed out")
            return False

    finally:
        await publisher.close()


async def test_post(images: list, caption: str, location: str = None):
    """Test posting functionality."""
    print("=" * 60)
    print("Testing Xiaohongshu Post Publishing")
    print("=" * 60)

    publisher = XiaohongshuPlaywrightPublisher(headless=False)

    try:
        result = await publisher.publish_post(
            images=images,
            caption=caption,
            location=location,
            auto_login=True,
        )

        print()
        print("Result:")
        for key, value in result.items():
            print(f"  {key}: {value}")

        return result.get("success", False)

    finally:
        await publisher.close()


def main():
    parser = argparse.ArgumentParser(description="Test Xiaohongshu Publisher")
    parser.add_argument("--login", action="store_true", help="Test login only")
    parser.add_argument("--test", action="store_true", help="Full test with sample images")
    parser.add_argument("--images", nargs="+", help="Image paths for testing")
    parser.add_argument("--caption", default="测试帖子 #测试", help="Caption for test post")
    parser.add_argument("--location", help="Location tag")

    args = parser.parse_args()

    if args.login:
        success = asyncio.run(test_login())
        sys.exit(0 if success else 1)

    if args.test:
        if not args.images:
            print("Error: --images required for test post")
            print(
                "Example: python test_xiaohongshu_publisher.py --test --images image1.jpg image2.jpg"
            )
            sys.exit(1)

        for img in args.images:
            if not Path(img).exists():
                print(f"Error: Image not found: {img}")
                sys.exit(1)

        success = asyncio.run(
            test_post(
                images=args.images,
                caption=args.caption,
                location=args.location,
            )
        )
        sys.exit(0 if success else 1)

    parser.print_help()


if __name__ == "__main__":
    main()
