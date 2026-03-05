"""Baidu Tieba (百度贴吧) Playwright Publisher

使用 Playwright 浏览器自动化实现百度贴吧发帖功能。

主要功能:
- 浏览器自动化发帖
- Cookie 会话持久化（避免重复登录）
- 帖子标题和内容
- 图片上传支持
- CDP 模式支持（使用真实 Chrome 浏览器，反检测效果更好）

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
import subprocess
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
    - CDP 模式（使用真实 Chrome 浏览器）
    """

    TIEBA_URL = "https://tieba.baidu.com"
    BAIDU_URL = "https://www.baidu.com"

    DEFAULT_TIMEOUT = 30000
    UPLOAD_TIMEOUT = 60000
    LOGIN_TIMEOUT = 120000

    COOKIE_DIR = Path("data/platform_sessions")
    COOKIE_FILE = COOKIE_DIR / "tieba_cookies.json"

    # CDP 模式配置
    CDP_DEBUG_PORT = 9222
    CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

    def __init__(
        self,
        headless: bool = True,
        cookie_path: Optional[str] = None,
        slow_mo: int = 100,
        enable_cdp: bool = True,
    ):
        self.settings = get_settings()
        self.headless = headless
        self.slow_mo = slow_mo
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None
        self.enable_cdp = enable_cdp
        self.chrome_process = None

        if cookie_path:
            self.cookie_file = Path(cookie_path)
        else:
            self.cookie_file = self.COOKIE_FILE

        self.cookie_file.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"TiebaPlaywrightPublisher initialized, headless={headless}, cdp={enable_cdp}")

    async def _ensure_browser(self) -> None:
        if self.browser is None:
            from playwright.async_api import async_playwright

            self.playwright = await async_playwright().start()

            if self.enable_cdp:
                self.browser = await self._launch_cdp_browser()
            else:
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

    async def _launch_cdp_browser(self):
        """启动 CDP 模式浏览器（使用真实 Chrome）。"""
        import socket

        port = self.CDP_DEBUG_PORT
        while True:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect(("127.0.0.1", port))
                port += 1
            except ConnectionRefusedError:
                break

        logger.info(f"Starting Chrome with CDP on port {port}")

        user_data_dir = Path.home() / ".kaitian_chrome_profile"
        user_data_dir.mkdir(parents=True, exist_ok=True)

        chrome_cmd = [
            self.CHROME_PATH,
            f"--remote-debugging-port={port}",
            f"--user-data-dir={user_data_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-background-networking",
            "--disable-client-side-phishing-detection",
            "--disable-default-apps",
            "--disable-extensions",
            "--disable-sync",
            "--disable-translate",
            "--metrics-recording-only",
            "--safebrowsing-disable-auto-update",
        ]

        self.chrome_process = subprocess.Popen(
            chrome_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        await asyncio.sleep(3)

        cdp_url = f"http://127.0.0.1:{port}"
        logger.info(f"Connecting to Chrome CDP: {cdp_url}")

        browser = await self.playwright.chromium.connect_over_cdp(cdp_url)
        logger.info("Connected to Chrome via CDP")

        return browser

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
            await asyncio.sleep(2)

            current_url = self.page.url
            page_title = await self.page.title()

            logger.info(f"Current URL: {current_url}")
            logger.info(f"Page title: {page_title}")

            if "wappass.baidu.com" in current_url or "captcha" in current_url:
                logger.info("Detected captcha/verification page - need user action")
                return False

            if "passport.baidu.com" in current_url or "login" in current_url.lower():
                logger.info("Detected login page - need user to login")
                return False

            login_user_selectors = [
                ".u_login_item",
                ".user_name",
                ".u_logout",
                '[class*="username"]',
                '[class*="user-name"]',
                ".nav_login_wap",
            ]

            for selector in login_user_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        text = await element.text_content()
                        if text and len(text.strip()) > 0 and "登录" not in text:
                            logger.info(f"Login verified - found user element: {selector}")
                            return True
                except Exception:
                    pass

            try:
                login_btn = await self.page.query_selector(
                    'a[href*="passport"], .login_btn, text="登录"'
                )
                if login_btn:
                    logger.info("Found login button - not logged in")
                    return False
            except Exception:
                pass

            logger.info("Login status unclear - assuming not logged in")
            return False

        except Exception as e:
            logger.error(f"Failed to check login status: {e}")
            return False

    async def wait_for_login(self, timeout: int = None) -> bool:
        timeout = timeout or self.LOGIN_TIMEOUT
        await self._ensure_context()

        try:
            await self.page.goto(self.TIEBA_URL, wait_until="networkidle")

            logger.info("Waiting for user login...")
            print("\n" + "=" * 60)
            print("请在浏览器中完成百度登录（验证码 + 扫码/账号密码）")
            print("=" * 60 + "\n")

            start_time = time.time()

            while time.time() - start_time < timeout / 1000:
                current_url = self.page.url

                if "wappass.baidu.com" in current_url or "captcha" in current_url:
                    logger.info("On verification page - waiting for user to complete...")
                    await asyncio.sleep(2)
                    continue

                if "passport.baidu.com" in current_url:
                    logger.info("On login page - waiting for user to login...")
                    await asyncio.sleep(2)
                    continue

                if "tieba.baidu.com" in current_url and "passport" not in current_url:
                    login_user_selectors = [
                        ".u_login_item",
                        ".user_name",
                        ".u_logout",
                        '[class*="username"]',
                    ]

                    for selector in login_user_selectors:
                        try:
                            element = await self.page.query_selector(selector)
                            if element:
                                text = await element.text_content()
                                if text and len(text.strip()) > 0 and "登录" not in text:
                                    logger.info("Login successful - found user element")
                                    await self._save_cookies()
                                    return True
                        except Exception:
                            pass

                    try:
                        login_btn = await self.page.query_selector(
                            'a[href*="passport"], .login_btn'
                        )
                        if not login_btn:
                            logger.info("Login successful - no login button found")
                            await self._save_cookies()
                            return True
                    except Exception:
                        pass

                await asyncio.sleep(2)

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
                "a.add_thread_btn",
                "a[title='发表新贴']",
                ".post_head_btn.add_thread_btn",
                "a:has-text('发表新贴')",
            ]

            for selector in post_btn_selectors:
                try:
                    btn = await self.page.wait_for_selector(selector, timeout=5000)
                    if btn:
                        is_visible = await btn.is_visible()
                        if is_visible:
                            await btn.click()
                            logger.info(f"Clicked post button: {selector}")
                            await asyncio.sleep(2)
                            return True
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue

            logger.error("Could not find post button")
            return False

        except Exception as e:
            logger.error(f"Failed to click post button: {e}")
            return False

    async def _fill_title(self, title: str) -> bool:
        try:
            title_selectors = [
                "input.title_input",
                "#tb_rich_poster_title",
                "input[placeholder*='标题']",
                ".title_container input",
                "input.editor_title",
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

    async def _close_popups(self) -> None:
        close_selectors = [
            ".ui_bubble_closed",
            ".j_close",
            ".close-btn",
            ".close_msg_tip",
            ".dialog_close",
            ".modal-close",
            "[class*='close']",
        ]

        for selector in close_selectors:
            try:
                close_btns = await self.page.query_selector_all(selector)
                for close_btn in close_btns:
                    is_visible = await close_btn.is_visible()
                    if is_visible:
                        await close_btn.click(force=True)
                        await asyncio.sleep(0.3)
                        logger.info(f"Closed popup: {selector}")
            except Exception:
                pass

    async def _fill_content(self, content: str) -> bool:
        try:
            await asyncio.sleep(1)
            await self._close_popups()

            escaped_content = (
                content.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "<br>")
            )
            try:
                await self.page.evaluate(f"""
                    const editor = document.querySelector('#ueditor_replace');
                    if (editor) {{
                        editor.innerHTML = '<p>{escaped_content}</p>';
                        editor.focus();
                    }}
                """)
                await asyncio.sleep(0.5)
                logger.info(f"Content set via JavaScript: {content[:30]}...")
                return True
            except Exception as e:
                logger.warning(f"JavaScript content set failed: {e}")

            content_selectors = [
                "#ueditor_replace",
                ".edui-body-container",
                "div[contenteditable='true']",
            ]

            for selector in content_selectors:
                try:
                    content_input = await self.page.wait_for_selector(selector, timeout=5000)
                    if content_input:
                        await content_input.scroll_into_view_if_needed()
                        await asyncio.sleep(0.3)
                        await content_input.click(force=True)
                        await asyncio.sleep(0.5)
                        await self._close_popups()
                        await content_input.focus()
                        await asyncio.sleep(0.3)
                        await self.page.keyboard.type(content, delay=20)
                        await asyncio.sleep(0.5)
                        logger.info(f"Content filled: {content[:30]}...")
                        return True
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
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
                "button.poster_submit",
                "button.j_submit",
                ".btn_default.j_submit",
                "button[title*='发表']",
                "button:has-text('发表')",
            ]

            for selector in submit_selectors:
                try:
                    submit_btn = await self.page.wait_for_selector(selector, timeout=5000)
                    if submit_btn:
                        is_visible = await submit_btn.is_visible()
                        if is_visible:
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

            if self.chrome_process:
                self.chrome_process.terminate()
                try:
                    self.chrome_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.chrome_process.kill()

            self.page = None
            self.context = None
            self.browser = None
            self.playwright = None
            self.chrome_process = None

            logger.info("Browser closed")

        except Exception as e:
            logger.error(f"Error closing browser: {e}")

    async def __aenter__(self):
        await self._ensure_context()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


tieba_publisher = TiebaPlaywrightPublisher()
