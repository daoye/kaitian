"""Xiaohongshu (小红书/RED) Playwright Publisher

使用 Playwright 浏览器自动化实现小红书帖子发布功能。

主要功能:
- 浏览器自动化发布帖子
- Cookie 会话持久化（避免重复登录）
- 图片上传支持
- 文字描述和话题标签
- 反检测措施

使用方式:
    publisher = XiaohongshuPlaywrightPublisher()
    result = await publisher.publish_post(
        images=["/path/to/image1.jpg", "/path/to/image2.jpg"],
        caption="帖子内容 #话题标签",
        location="上海"  # 可选
    )
"""

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class XiaohongshuPlaywrightPublisher:
    """小红书 Playwright 发布器

    使用 Playwright 进行浏览器自动化，实现小红书帖子的自动发布。
    支持:
    - 多图上传
    - 文字描述
    - 话题标签
    - 地点标记
    - Cookie 持久化
    """

    # 小红书相关 URL
    CREATOR_URL = "https://creator.xiaohongshu.com"
    LOGIN_URL = "https://creator.xiaohongshu.com/login"
    PUBLISH_URL = "https://creator.xiaohongshu.com/publish/publish"

    # 超时设置
    DEFAULT_TIMEOUT = 30000  # 30 秒
    UPLOAD_TIMEOUT = 60000  # 60 秒（上传可能较慢）
    LOGIN_TIMEOUT = 120000  # 120 秒（登录等待时间）

    # Cookie 存储路径
    COOKIE_DIR = Path("data/platform_sessions")
    COOKIE_FILE = COOKIE_DIR / "xiaohongshu_cookies.json"

    def __init__(
        self,
        headless: bool = True,
        cookie_path: Optional[str] = None,
        slow_mo: int = 100,  # 操作间隔，模拟人类行为
    ):
        """初始化发布器

        Args:
            headless: 是否使用无头模式
            cookie_path: Cookie 存储路径，默认使用 data/platform_sessions/
            slow_mo: 操作间隔毫秒数，用于模拟人类行为
        """
        self.settings = get_settings()
        self.headless = headless
        self.slow_mo = slow_mo
        self.browser = None
        self.context = None
        self.page = None

        # Cookie 存储路径
        if cookie_path:
            self.cookie_file = Path(cookie_path)
        else:
            self.cookie_file = self.COOKIE_FILE

        # 确保 Cookie 目录存在
        self.cookie_file.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"XiaohongshuPlaywrightPublisher initialized, headless={headless}")

    async def _ensure_browser(self) -> None:
        """确保浏览器实例已启动"""
        if self.browser is None:
            from playwright.async_api import async_playwright

            self.playwright = await async_playwright().start()

            # 配置浏览器启动参数（反检测）
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )

            logger.info("Browser launched successfully")

    async def _ensure_context(self) -> None:
        """确保浏览器上下文已创建，并加载已保存的 Cookie"""
        await self._ensure_browser()

        if self.context is None:
            # 创建浏览器上下文（模拟真实浏览器环境）
            self.context = await self.browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="zh-CN",
                timezone_id="Asia/Shanghai",
            )

            # 加载已保存的 Cookie
            await self._load_cookies()

            # 创建页面
            self.page = await self.context.new_page()

            # 设置默认超时
            self.page.set_default_timeout(self.DEFAULT_TIMEOUT)

            logger.info("Browser context created")

    async def _load_cookies(self) -> bool:
        """加载已保存的 Cookie

        Returns:
            是否成功加载 Cookie
        """
        if self.cookie_file.exists():
            try:
                with open(self.cookie_file, "r", encoding="utf-8") as f:
                    cookies = json.load(f)

                if cookies:
                    await self.context.add_cookies(cookies)
                    logger.info(f"Loaded {len(cookies)} cookies from {self.cookie_file}")
                    return True
            except Exception as e:
                logger.warning(f"Failed to load cookies: {e}")

        return False

    async def _save_cookies(self) -> bool:
        """保存当前 Cookie

        Returns:
            是否成功保存 Cookie
        """
        try:
            cookies = await self.context.cookies()

            with open(self.cookie_file, "w", encoding="utf-8") as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)

            logger.info(f"Saved {len(cookies)} cookies to {self.cookie_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save cookies: {e}")
            return False

    async def _check_login_status(self) -> bool:
        """检查是否已登录

        Returns:
            是否已登录
        """
        await self._ensure_context()

        try:
            # 访问创作者中心
            await self.page.goto(self.CREATOR_URL, wait_until="networkidle")

            # 检查是否重定向到登录页面
            current_url = self.page.url

            if "login" in current_url:
                logger.info("Not logged in - redirected to login page")
                return False

            # 检查是否有发布按钮或用户头像（登录状态标识）
            # 使用多种选择器尝试
            selectors = [
                'button:has-text("发布笔记")',
                'a:has-text("发布笔记")',
                ".avatar-wrapper",
                ".user-avatar",
                '[class*="publish"]',
            ]

            for selector in selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=5000)
                    if element:
                        logger.info("Login verified - found user elements")
                        return True
                except Exception:
                    continue

            logger.info("Login status unclear - no user elements found")
            return False

        except Exception as e:
            logger.error(f"Failed to check login status: {e}")
            return False

    async def wait_for_login(self, timeout: int = None) -> bool:
        """等待用户登录（扫描二维码或手机登录）

        Args:
            timeout: 超时时间（毫秒）

        Returns:
            是否登录成功
        """
        timeout = timeout or self.LOGIN_TIMEOUT
        await self._ensure_context()

        try:
            # 导航到登录页面
            await self.page.goto(self.LOGIN_URL, wait_until="networkidle")

            logger.info("Waiting for user login (QR code or phone)...")
            print("\n" + "=" * 60)
            print("请在浏览器中完成小红书登录（扫描二维码或手机登录）")
            print("=" * 60 + "\n")

            # 等待登录成功（检测 URL 变化或登录元素消失）
            start_time = time.time()

            while time.time() - start_time < timeout / 1000:
                current_url = self.page.url

                # 如果跳转到创作者中心，说明登录成功
                if "login" not in current_url:
                    logger.info("Login successful - redirected away from login page")
                    await self._save_cookies()
                    return True

                # 检查是否有发布按钮
                try:
                    publish_btn = await self.page.query_selector('button:has-text("发布笔记")')
                    if publish_btn:
                        logger.info("Login successful - found publish button")
                        await self._save_cookies()
                        return True
                except Exception:
                    pass

                await asyncio.sleep(1)

            logger.warning("Login timeout - user did not complete login")
            return False

        except Exception as e:
            logger.error(f"Error during login wait: {e}")
            return False

    async def _navigate_to_publish(self) -> bool:
        """导航到发布页面

        Returns:
            是否成功导航
        """
        try:
            # 直接访问发布页面
            await self.page.goto(self.PUBLISH_URL, wait_until="networkidle")

            # 检查是否需要登录
            if "login" in self.page.url:
                logger.warning("Redirected to login page - need to login first")
                return False

            # 等待上传区域出现
            await self.page.wait_for_selector('input[type="file"]', timeout=self.DEFAULT_TIMEOUT)

            logger.info("Navigated to publish page successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to navigate to publish page: {e}")
            return False

    async def _upload_images(self, image_paths: List[str]) -> bool:
        """上传图片

        Args:
            image_paths: 图片文件路径列表

        Returns:
            是否上传成功
        """
        try:
            # 验证图片文件存在
            valid_paths = []
            for path in image_paths:
                if os.path.exists(path):
                    valid_paths.append(path)
                else:
                    logger.warning(f"Image file not found: {path}")

            if not valid_paths:
                logger.error("No valid image files to upload")
                return False

            # 查找文件上传 input
            file_input = await self.page.query_selector('input[type="file"]')

            if not file_input:
                logger.error("Could not find file input element")
                return False

            # 上传图片
            await file_input.set_input_files(valid_paths)

            logger.info(f"Uploading {len(valid_paths)} images...")

            # 等待上传完成
            # 检测上传进度或预览图出现
            await asyncio.sleep(2)  # 给予上传时间

            # 等待图片预览出现
            try:
                await self.page.wait_for_selector(
                    '[class*="image-preview"], [class*="upload-item"], [class*="img-item"]',
                    timeout=self.UPLOAD_TIMEOUT,
                )
                logger.info("Images uploaded successfully")
                return True
            except Exception:
                # 可能没有预览元素，检查上传进度条消失
                logger.info("Upload may have completed (no preview element found)")
                return True

        except Exception as e:
            logger.error(f"Failed to upload images: {e}")
            return False

    async def _fill_caption(self, caption: str) -> bool:
        """填写帖子描述

        Args:
            caption: 帖子描述文本（可包含 #话题标签）

        Returns:
            是否填写成功
        """
        try:
            # 小红书的描述输入框可能有多种选择器
            caption_selectors = [
                'textarea[placeholder*="填写正文"]',
                'textarea[placeholder*="描述"]',
                'textarea[placeholder*="内容"]',
                ".content-input textarea",
                '[class*="caption"] textarea',
                '[class*="content"] textarea',
                "#post-textarea",
                'div[contenteditable="true"]',
            ]

            caption_input = None
            for selector in caption_selectors:
                try:
                    caption_input = await self.page.wait_for_selector(selector, timeout=5000)
                    if caption_input:
                        break
                except Exception:
                    continue

            if not caption_input:
                logger.error("Could not find caption input element")
                return False

            # 点击输入框获取焦点
            await caption_input.click()
            await asyncio.sleep(0.3)

            # 输入文本
            await caption_input.fill(caption)

            logger.info(f"Caption filled: {caption[:50]}...")
            return True

        except Exception as e:
            logger.error(f"Failed to fill caption: {e}")
            return False

    async def _add_location(self, location: str) -> bool:
        """添加地点标签

        Args:
            location: 地点名称

        Returns:
            是否添加成功
        """
        try:
            # 查找地点添加按钮
            location_btn_selectors = [
                'button:has-text("添加地点")',
                'div:has-text("添加地点")',
                '[class*="location-add"]',
                '[class*="add-location"]',
            ]

            for selector in location_btn_selectors:
                try:
                    btn = await self.page.wait_for_selector(selector, timeout=3000)
                    if btn:
                        await btn.click()
                        break
                except Exception:
                    continue
            else:
                logger.warning("Could not find location add button")
                return False

            await asyncio.sleep(0.5)

            # 在搜索框输入地点
            search_input = await self.page.wait_for_selector(
                'input[placeholder*="搜索地点"], input[placeholder*="搜索"]', timeout=5000
            )

            if search_input:
                await search_input.fill(location)
                await asyncio.sleep(1)

                # 点击搜索结果
                first_result = await self.page.wait_for_selector(
                    '[class*="location-item"], [class*="search-result"]', timeout=5000
                )

                if first_result:
                    await first_result.click()
                    logger.info(f"Location added: {location}")
                    return True

            return False

        except Exception as e:
            logger.warning(f"Failed to add location: {e} (non-critical)")
            return False

    async def _click_publish(self) -> bool:
        """点击发布按钮

        Returns:
            是否发布成功
        """
        try:
            # 查找发布按钮
            publish_btn_selectors = [
                'button:has-text("发布")',
                'button:has-text("发布笔记")',
                'button[class*="publish-btn"]',
                'button[class*="submit"]',
                ".publish-btn",
                ".submit-btn",
            ]

            publish_btn = None
            for selector in publish_btn_selectors:
                try:
                    publish_btn = await self.page.wait_for_selector(selector, timeout=5000)
                    if publish_btn:
                        break
                except Exception:
                    continue

            if not publish_btn:
                logger.error("Could not find publish button")
                return False

            # 滚动到按钮位置
            await publish_btn.scroll_into_view_if_needed()
            await asyncio.sleep(0.3)

            # 点击发布
            await publish_btn.click()

            logger.info("Publish button clicked")

            # 等待发布完成
            # 检测成功提示或页面跳转
            await asyncio.sleep(3)

            # 检查是否有成功提示
            success_indicators = [
                "text=发布成功",
                "text=已发布",
                "text=审核中",
                '[class*="success"]',
            ]

            for indicator in success_indicators:
                try:
                    await self.page.wait_for_selector(indicator, timeout=10000)
                    logger.info("Post published successfully!")
                    return True
                except Exception:
                    continue

            # 检查是否跳转到其他页面
            current_url = self.page.url
            if "publish" not in current_url:
                logger.info("Page navigated away - post likely published")
                return True

            logger.warning("Could not confirm publish success, but no errors detected")
            return True

        except Exception as e:
            logger.error(f"Failed to publish: {e}")
            return False

    async def publish_post(
        self,
        images: List[str],
        caption: str,
        location: Optional[str] = None,
        auto_login: bool = True,
    ) -> Dict[str, Any]:
        """发布小红书帖子

        Args:
            images: 图片文件路径列表（1-9张）
            caption: 帖子描述（可包含 #话题标签）
            location: 地点标签（可选）
            auto_login: 是否自动等待登录

        Returns:
            {
                "success": bool,
                "post_id": str (可选),
                "post_url": str (可选),
                "platform": "xiaohongshu",
                "error": str (可选)
            }
        """
        result = {
            "success": False,
            "platform": "xiaohongshu",
        }

        try:
            # 确保浏览器已启动
            await self._ensure_context()

            # 检查登录状态
            if not await self._check_login_status():
                if auto_login:
                    logger.info("Not logged in, waiting for user login...")
                    if not await self.wait_for_login():
                        result["error"] = "Login failed or timed out"
                        return result
                else:
                    result["error"] = "Not logged in"
                    return result

            # 导航到发布页面
            if not await self._navigate_to_publish():
                result["error"] = "Failed to navigate to publish page"
                return result

            # 上传图片
            if not await self._upload_images(images):
                result["error"] = "Failed to upload images"
                return result

            # 填写描述
            if not await self._fill_caption(caption):
                result["error"] = "Failed to fill caption"
                return result

            # 添加地点（可选）
            if location:
                await self._add_location(location)

            # 发布
            if not await self._click_publish():
                result["error"] = "Failed to publish post"
                return result

            result["success"] = True
            result["message"] = "Post published successfully"

            # 尝试获取帖子 URL（如果有）
            try:
                current_url = self.page.url
                if "/note/" in current_url or "/explore/" in current_url:
                    result["post_url"] = current_url
            except Exception:
                pass

            return result

        except Exception as e:
            logger.error(f"Failed to publish post: {e}")
            result["error"] = str(e)
            return result

    async def close(self) -> None:
        """关闭浏览器"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if hasattr(self, "playwright"):
                await self.playwright.stop()

            self.page = None
            self.context = None
            self.browser = None

            logger.info("Browser closed")

        except Exception as e:
            logger.error(f"Error closing browser: {e}")

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self._ensure_context()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()


# 创建全局实例
xiaohongshu_publisher = XiaohongshuPlaywrightPublisher()
