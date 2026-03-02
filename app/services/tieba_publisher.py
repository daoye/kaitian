"""Baidu Tieba (百度贴吧) Playwright Publisher

使用 Playwright 浏览器自动化实现百度贴吧发帖功能。

主要功能:
- 浏览器自动化发帖
- Cookie 会话持久化（避免重复登录）
- 帖子标题和内容
- 图片上传支持
- 反检测措施

使用方式:
    publisher = TiebaPlaywrightPublisher()
    result = await publisher.publish_post(
        forum_name="python",
        title="帖子标题",
        content="帖子内容",
        images=["/path/to/image1.jpg"]  # 可选
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


class TiebaPlaywrightPublisher:
    """百度贴吧 Playwright 发布器

    使用 Playwright 进行浏览器自动化，实现百度贴吧帖子的自动发布。
    支持:
    - 指定贴吧发帖
    - 帖子标题和内容
    - 图片上传
    - Cookie 持久化
    """

    TIEBA_URL = "https://tieba.baidu.com"
    BAIDU_URL = "https://www.baidu.com"

    DEFAULT_TIMEOUT = 30000
    UPLOAD_TIMEOUT = 60000
    LOGIN_TIMEOUT = 120000

    COOKIE_DIR = Path("data/platform_sessions")
    COOKIE_FILE = COOKIE_DIR / "tieba_cookies.json"

    def __init__(
        self,
        headless: bool = True,
        cookie_path: Optional[str] = None,
        slow_mo: int = 100,
    ):
        self.settings = get_settings()
        self.headless = headless
        self.slow_mo = slow_mo
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None

        if cookie_path:
            self.cookie_file = Path(cookie_path)
        else:
            self.cookie_file = self.COOKIE_FILE

        self.cookie_file.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"TiebaPlaywrightPublisher initialized, headless={headless}")

    async def _ensure_browser(self) -> None:
        if self.browser is None:
            from playwright.async_api import async_playwright

            self.playwright = await async_playwright().start()

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
        await self._ensure_browser()

        if self.context is None:
            self.context = await self.browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="zh-CN",
                timezone_id="Asia/Shanghai",
            )

            await self._load_cookies()

            self.page = await self.context.new_page()
            self.page.set_default_timeout(self.DEFAULT_TIMEOUT)

            logger.info("Browser context created")

    async def _load_cookies(self) -> bool:
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
        await self._ensure_context()

        try:
            await self.page.goto(self.TIEBA_URL, wait_until="networkidle")

            current_cookies = await self.context.cookies()
            cookie_dict = {c["name"]: c["value"] for c in current_cookies}

            stoken = cookie_dict.get("STOKEN")
            ptoken = cookie_dict.get("PTOKEN")
            bduss = cookie_dict.get("BDUSS")

            if stoken or ptoken or bduss:
                logger.info("Login verified - found Baidu auth cookies")
                return True

            login_selectors = [
                ".u_login",
                ".login-btn",
                'a[href*="passport"]',
                ".user_info",
            ]

            for selector in login_selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=3000)
                    if element:
                        is_login = "login" not in selector.lower() or "user" in selector.lower()
                        if is_login:
                            logger.info("Login verified - found user elements")
                            return True
                except Exception:
                    continue

            logger.info("Not logged in")
            return False

        except Exception as e:
            logger.error(f"Failed to check login status: {e}")
            return False

    async def wait_for_login(self, timeout: int = None) -> bool:
        timeout = timeout or self.LOGIN_TIMEOUT
        await self._ensure_context()

        try:
            await self.page.goto(self.TIEBA_URL, wait_until="networkidle")

            logger.info("Waiting for user login (QR code or phone)...")
            print("\n" + "=" * 60)
            print("请在浏览器中完成百度登录（扫描二维码或账号密码登录）")
            print("=" * 60 + "\n")

            start_time = time.time()

            while time.time() - start_time < timeout / 1000:
                current_cookies = await self.context.cookies()
                cookie_dict = {c["name"]: c["value"] for c in current_cookies}

                stoken = cookie_dict.get("STOKEN")
                ptoken = cookie_dict.get("PTOKEN")
                bduss = cookie_dict.get("BDUSS")

                if stoken or ptoken or bduss:
                    logger.info("Login successful - found auth cookies")
                    await self._save_cookies()
                    return True

                await asyncio.sleep(1)

            logger.warning("Login timeout")
            return False

        except Exception as e:
            logger.error(f"Error during login wait: {e}")
            return False

    async def _navigate_to_forum(self, forum_name: str) -> bool:
        try:
            forum_url = f"https://tieba.baidu.com/f?kw={forum_name}"
            await self.page.goto(forum_url, wait_until="networkidle")

            await self.page.wait_for_selector(
                ".forum_title, h1, .card_title", timeout=self.DEFAULT_TIMEOUT
            )

            logger.info(f"Navigated to forum: {forum_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to navigate to forum {forum_name}: {e}")
            return False

    async def _click_post_button(self) -> bool:
        try:
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
                    btn = await self.page.wait_for_selector(selector, timeout=5000)
                    if btn:
                        await btn.click()
                        logger.info(f"Clicked post button: {selector}")
                        await asyncio.sleep(1)
                        return True
                except Exception:
                    continue

            logger.error("Could not find post button")
            return False

        except Exception as e:
            logger.error(f"Failed to click post button: {e}")
            return False

    async def _fill_title(self, title: str) -> bool:
        try:
            title_selectors = [
                "#title",
                'input[name="title"]',
                'input[placeholder*="标题"]',
                ".title_input",
                "#tb_title",
            ]

            for selector in title_selectors:
                try:
                    title_input = await self.page.wait_for_selector(selector, timeout=5000)
                    if title_input:
                        await title_input.click()
                        await asyncio.sleep(0.3)
                        await title_input.fill(title)
                        logger.info(f"Title filled: {title[:30]}...")
                        return True
                except Exception:
                    continue

            logger.error("Could not find title input")
            return False

        except Exception as e:
            logger.error(f"Failed to fill title: {e}")
            return False

    async def _fill_content(self, content: str) -> bool:
        try:
            content_selectors = [
                "#ueditor_replace",
                ".editor_content",
                'textarea[placeholder*="内容"]',
                ".content_input",
                "#tb_editor",
                'div[contenteditable="true"]',
            ]

            for selector in content_selectors:
                try:
                    content_input = await self.page.wait_for_selector(selector, timeout=5000)
                    if content_input:
                        await content_input.click()
                        await asyncio.sleep(0.3)
                        await content_input.fill(content)
                        logger.info(f"Content filled: {content[:30]}...")
                        return True
                except Exception:
                    continue

            logger.error("Could not find content input")
            return False

        except Exception as e:
            logger.error(f"Failed to fill content: {e}")
            return False

    async def _upload_images(self, images: List[str]) -> bool:
        if not images:
            return True

        try:
            valid_paths = []
            for path in images:
                if os.path.exists(path):
                    valid_paths.append(path)
                else:
                    logger.warning(f"Image file not found: {path}")

            if not valid_paths:
                logger.warning("No valid images to upload")
                return True

            file_input_selectors = [
                'input[type="file"][accept*="image"]',
                'input[type="file"]',
                ".upload_input",
            ]

            for selector in file_input_selectors:
                try:
                    file_input = await self.page.query_selector(selector)
                    if file_input:
                        for img_path in valid_paths:
                            await file_input.set_input_files(img_path)
                            await asyncio.sleep(1)

                        logger.info(f"Uploaded {len(valid_paths)} images")
                        return True
                except Exception:
                    continue

            logger.warning("Could not find file input for images")
            return True

        except Exception as e:
            logger.warning(f"Failed to upload images: {e} (non-critical)")
            return True

    async def _submit_post(self) -> bool:
        try:
            submit_selectors = [
                'button[type="submit"]',
                ".submit_btn",
                "#submit_btn",
                'input[type="submit"]',
                "text=发表",
                "text=发布",
                ".tb_btn_submit",
            ]

            for selector in submit_selectors:
                try:
                    submit_btn = await self.page.wait_for_selector(selector, timeout=5000)
                    if submit_btn:
                        await submit_btn.scroll_into_view_if_needed()
                        await asyncio.sleep(0.3)
                        await submit_btn.click()
                        logger.info(f"Clicked submit button: {selector}")
                        return True
                except Exception:
                    continue

            logger.error("Could not find submit button")
            return False

        except Exception as e:
            logger.error(f"Failed to submit post: {e}")
            return False

    async def _verify_post_success(self) -> Dict[str, Any]:
        await asyncio.sleep(3)

        current_url = self.page.url

        if "post" not in current_url and "thread" in current_url:
            logger.info("Post published successfully - URL changed to thread")
            return {
                "success": True,
                "post_url": current_url,
            }

        success_indicators = [
            "text=发表成功",
            "text=发布成功",
            ".success_msg",
            ".post_success",
        ]

        for indicator in success_indicators:
            try:
                await self.page.wait_for_selector(indicator, timeout=5000)
                logger.info(f"Post success detected: {indicator}")

                post_url = current_url
                thread_id = None

                if "thread" in current_url or "post" not in current_url:
                    post_url = current_url
                else:
                    try:
                        new_url = self.page.url
                        if new_url != current_url:
                            post_url = new_url
                    except Exception:
                        pass

                return {
                    "success": True,
                    "post_url": post_url,
                }
            except Exception:
                continue

        logger.info("Post submission completed (status unclear)")
        return {
            "success": True,
            "message": "Post submitted, please verify manually",
        }

    async def publish_post(
        self,
        forum_name: str,
        title: str,
        content: str,
        images: Optional[List[str]] = None,
        auto_login: bool = True,
    ) -> Dict[str, Any]:
        result = {
            "success": False,
            "platform": "tieba",
            "forum": forum_name,
        }

        try:
            await self._ensure_context()

            if not await self._check_login_status():
                if auto_login:
                    logger.info("Not logged in, waiting for user login...")
                    if not await self.wait_for_login():
                        result["error"] = "Login failed or timed out"
                        return result
                else:
                    result["error"] = "Not logged in"
                    return result

            if not await self._navigate_to_forum(forum_name):
                result["error"] = f"Failed to navigate to forum: {forum_name}"
                return result

            if not await self._click_post_button():
                result["error"] = "Failed to open post editor"
                return result

            await asyncio.sleep(1)

            if not await self._fill_title(title):
                result["error"] = "Failed to fill title"
                return result

            if not await self._fill_content(content):
                result["error"] = "Failed to fill content"
                return result

            if images:
                await self._upload_images(images)

            if not await self._submit_post():
                result["error"] = "Failed to submit post"
                return result

            verify_result = await self._verify_post_success()
            result.update(verify_result)

            return result

        except Exception as e:
            logger.error(f"Failed to publish post: {e}")
            result["error"] = str(e)
            return result

    async def close(self) -> None:
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()

            self.page = None
            self.context = None
            self.browser = None
            self.playwright = None

            logger.info("Browser closed")

        except Exception as e:
            logger.error(f"Error closing browser: {e}")

    async def __aenter__(self):
        await self._ensure_context()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


tieba_publisher = TiebaPlaywrightPublisher()
