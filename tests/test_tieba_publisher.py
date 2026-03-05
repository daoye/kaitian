#!/usr/bin/env python3
"""测试百度贴吧 Playwright 发布器

Usage:
    uv run python tests/test_tieba_publisher.py --login    # 仅测试登录
    uv run python tests/test_tieba_publisher.py --post     # 测试发帖
"""

import asyncio
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.tieba_publisher import TiebaPlaywrightPublisher


async def test_login():
    """测试登录功能。"""
    print("=" * 60)
    print("测试百度贴吧登录 (CDP 模式)")
    print("=" * 60)

    publisher = TiebaPlaywrightPublisher(headless=False, enable_cdp=True)

    try:
        print("\n正在启动浏览器 (CDP 模式 - 使用真实 Chrome)...")
        await publisher._ensure_context()
        print("浏览器上下文已创建")

        print("\n正在检查登录状态...")
        if await publisher._check_login_status():
            print("✓ 已经登录!")
            return True

        print("\n正在导航到贴吧首页...")
        await publisher.page.goto("https://tieba.baidu.com", wait_until="networkidle")
        print(f"当前 URL: {publisher.page.url}")
        print(f"页面标题: {await publisher.page.title()}")

        print("\n等待登录...")
        print("请在浏览器中完成：1. 验证码验证  2. 扫码登录")
        print("等待时间：10 分钟")

        if await publisher.wait_for_login(timeout=600000):
            print("✓ 登录成功!")
            return True
        else:
            print("✗ 登录失败或超时")
            return False

    except Exception as e:
        print(f"\n发生错误: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        await publisher.close()


async def test_post(forum_name: str, title: str, content: str, images: list = None):
    """测试发帖功能。"""
    print("=" * 60)
    print("测试百度贴吧发帖 (CDP 模式)")
    print("=" * 60)

    publisher = TiebaPlaywrightPublisher(headless=False, enable_cdp=True)

    try:
        result = await publisher.publish_post(
            forum_name=forum_name,
            title=title,
            content=content,
            images=images,
            auto_login=True,
        )

        print()
        print("结果:")
        for key, value in result.items():
            print(f"  {key}: {value}")

        return result.get("success", False)

    finally:
        await publisher.close()


async def debug_page_elements(forum_name: str):
    """调试页面元素 - 打印页面结构和选择器。"""
    print("=" * 60)
    print("调试百度贴吧页面元素")
    print("=" * 60)

    publisher = TiebaPlaywrightPublisher(headless=False)

    try:
        await publisher._ensure_context()

        # 检查登录
        if not await publisher._check_login_status():
            print("等待登录...")
            if not await publisher.wait_for_login():
                print("✗ 登录失败")
                return

        # 导航到贴吧
        forum_url = f"https://tieba.baidu.com/f?kw={forum_name}"
        print(f"\n导航到: {forum_url}")
        await publisher.page.goto(forum_url, wait_until="networkidle")
        await asyncio.sleep(2)

        # 打印页面标题
        print(f"\n页面标题: {await publisher.page.title()}")
        print(f"当前 URL: {publisher.page.url}")

        # 查找发帖按钮
        print("\n--- 查找发帖按钮 ---")
        post_btn_selectors = [
            'a[href*="post"]',
            ".post_btn",
            "#new_topic_btn",
            "a.j_post_btn",
            ".tb_btn_create",
            "text=发帖",
        ]

        for selector in post_btn_selectors:
            try:
                elements = await publisher.page.query_selector_all(selector)
                if elements:
                    print(f"找到 {len(elements)} 个元素: {selector}")
                    for i, el in enumerate(elements[:3]):
                        try:
                            text = await el.text_content()
                            href = await el.get_attribute("href")
                            print(f"  [{i}] text={text}, href={href}")
                        except:
                            pass
            except Exception as e:
                pass

        # 打印页面 HTML 片段（发帖区域）
        print("\n--- 页面 HTML 片段 ---")
        try:
            html = await publisher.page.content()
            # 保存到文件
            debug_file = Path("logs/tieba_debug.html")
            debug_file.parent.mkdir(parents=True, exist_ok=True)
            with open(debug_file, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"已保存页面 HTML 到: {debug_file}")
        except Exception as e:
            print(f"保存 HTML 失败: {e}")

        # 等待用户查看
        print("\n按 Enter 继续...")
        input()

    finally:
        await publisher.close()


def main():
    parser = argparse.ArgumentParser(description="测试百度贴吧发布器")
    parser.add_argument("--login", action="store_true", help="仅测试登录")
    parser.add_argument("--post", action="store_true", help="测试发帖")
    parser.add_argument("--debug", action="store_true", help="调试页面元素")
    parser.add_argument("--forum", default="python", help="贴吧名称")
    parser.add_argument("--title", default="测试帖子 - 自动发布测试", help="帖子标题")
    parser.add_argument(
        "--content",
        default="这是一个测试帖子，用于验证 Playwright 自动化发布功能。",
        help="帖子内容",
    )
    parser.add_argument("--images", nargs="+", help="图片路径")

    args = parser.parse_args()

    if args.login:
        success = asyncio.run(test_login())
        sys.exit(0 if success else 1)

    if args.post:
        success = asyncio.run(
            test_post(
                forum_name=args.forum,
                title=args.title,
                content=args.content,
                images=args.images,
            )
        )
        sys.exit(0 if success else 1)

    if args.debug:
        asyncio.run(debug_page_elements(args.forum))
        sys.exit(0)

    parser.print_help()


if __name__ == "__main__":
    main()
