"""Generic Login Manager for multi-platform session management."""

import asyncio
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

STEALTH_JS_PATH = Path(__file__).parent.parent.parent.parent / "libs" / "stealth.min.js"


class Platform(str, Enum):
    TIEBA = "tieba"
    XIAOHONGSHU = "xiaohongshu"
    WEIBO = "weibo"
    ZHIHU = "zhihu"


@dataclass
class LoginState:
    platform: Platform
    is_logged_in: bool = False
    username: Optional[str] = None
    user_id: Optional[str] = None
    last_checked: Optional[float] = None
    cookies: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None


class PlatformLoginHandler(ABC):
    @abstractmethod
    async def check_login_status(self, page) -> bool:
        pass

    @abstractmethod
    async def wait_for_login(self, page, timeout: int) -> bool:
        pass

    @abstractmethod
    def get_login_url(self) -> str:
        pass

    @abstractmethod
    def get_home_url(self) -> str:
        pass


class TiebaLoginHandler(PlatformLoginHandler):
    PLATFORM = Platform.TIEBA
    TIEBA_URL = "https://tieba.baidu.com"
    BAIDU_URL = "https://www.baidu.com"

    async def check_login_status(self, page) -> bool:
        try:
            current_url = page.url

            if "passport.baidu.com" in current_url:
                return False

            if "wappass.baidu.com" in current_url or "captcha" in current_url:
                return False

            if "tieba.baidu.com" in current_url:
                try:
                    login_btn = await page.query_selector(
                        'a[href*="passport"], .login_btn, text="登录"'
                    )
                    if login_btn:
                        is_visible = await login_btn.is_visible()
                        if is_visible:
                            return False
                except Exception:
                    pass

                login_user_selectors = [
                    ".u_login_item",
                    ".user_name",
                    ".u_logout",
                    '[class*="username"]',
                    '[class*="user-name"]',
                    ".nav_login_wap",
                    ".user_info",
                    "#u_info",
                ]
                for selector in login_user_selectors:
                    try:
                        element = await page.query_selector(selector)
                        if element:
                            text = await element.text_content()
                            if text and len(text.strip()) > 0 and "登录" not in text:
                                logger.info(f"Login detected via selector: {selector}")
                                return True
                    except Exception:
                        pass

            return False
        except Exception as e:
            logger.error(f"Failed to check login status: {e}")
            return False

    async def wait_for_login(self, page, timeout: int = 300000) -> bool:
        try:
            logger.info("Waiting for user login...")
            print("\n" + "=" * 60)
            print("请在浏览器中完成百度登录")
            print("支持: 扫码登录 / 账号密码登录 / 短信验证")
            print("登录成功后将自动继续...")
            print("=" * 60 + "\n")

            start_time = time.time()
            check_count = 0

            while time.time() - start_time < timeout / 1000:
                check_count += 1
                current_url = page.url

                elapsed = int(time.time() - start_time)
                if check_count % 5 == 0:
                    logger.info(
                        f"Waiting for login... ({elapsed}s elapsed, URL: {current_url[:50]}...)"
                    )

                if "passport.baidu.com" in current_url:
                    await asyncio.sleep(2)
                    continue

                if "wappass.baidu.com" in current_url or "captcha" in current_url:
                    logger.info("CAPTCHA/verification page detected, waiting...")
                    await asyncio.sleep(3)
                    continue

                if await self.check_login_status(page):
                    logger.info("Login successful!")
                    print("\n" + "=" * 60)
                    print("✓ 登录成功！")
                    print("=" * 60 + "\n")
                    return True

                await asyncio.sleep(2)

            logger.warning(f"Login timeout after {timeout / 1000}s")
            print("\n⚠️ 登录超时，请重试")
            return False

        except Exception as e:
            logger.error(f"Error during login wait: {e}")
            return False

    def get_login_url(self) -> str:
        return self.TIEBA_URL

    def get_home_url(self) -> str:
        return self.TIEBA_URL


class XiaohongshuLoginHandler(PlatformLoginHandler):
    PLATFORM = Platform.XIAOHONGSHU
    CREATOR_URL = "https://creator.xiaohongshu.com"
    LOGIN_URL = "https://creator.xiaohongshu.com/login"

    async def check_login_status(self, page) -> bool:
        try:
            current_url = page.url
            if "login" in current_url:
                return False
            selectors = [
                'button:has-text("发布笔记")',
                'a:has-text("发布笔记")',
                ".avatar-wrapper",
                ".user-avatar",
                '[class*="publish"]',
            ]
            for selector in selectors:
                try:
                    element = await page.wait_for_selector(selector, timeout=5000)
                    if element:
                        return True
                except Exception:
                    continue
            return False
        except Exception as e:
            logger.error(f"Failed to check login status: {e}")
            return False

    async def wait_for_login(self, page, timeout: int = 120000) -> bool:
        try:
            logger.info("Waiting for user login (QR code or phone)...")
            print("\n" + "=" * 60)
            print("请在浏览器中完成小红书登录（扫描二维码或手机登录）")
            print("=" * 60 + "\n")
            start_time = time.time()
            while time.time() - start_time < timeout / 1000:
                current_url = page.url
                if "login" not in current_url:
                    return True
                try:
                    publish_btn = await page.query_selector('button:has-text("发布笔记")')
                    if publish_btn:
                        return True
                except Exception:
                    pass
                await asyncio.sleep(1)
            return False
        except Exception as e:
            logger.error(f"Error during login wait: {e}")
            return False

    def get_login_url(self) -> str:
        return self.LOGIN_URL

    def get_home_url(self) -> str:
        return self.CREATOR_URL


class LoginManager:
    COOKIE_DIR = Path("data/platform_sessions")
    BROWSER_DATA_DIR = Path("data/browser_data")

    def __init__(self):
        self.settings = get_settings()
        self._handlers: Dict[Platform, PlatformLoginHandler] = {}
        self._states: Dict[Platform, LoginState] = {}
        self._contexts: Dict[Platform, Any] = {}
        self._pages: Dict[Platform, Any] = {}
        self._playwright = None
        self._browser = None

        self.COOKIE_DIR.mkdir(parents=True, exist_ok=True)
        self.BROWSER_DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._register_handlers()

    def _register_handlers(self):
        self._handlers[Platform.TIEBA] = TiebaLoginHandler()
        self._handlers[Platform.XIAOHONGSHU] = XiaohongshuLoginHandler()

    def _get_cookie_file(self, platform: Platform) -> Path:
        return self.COOKIE_DIR / f"{platform.value}_cookies.json"

    def _get_user_data_dir(self, platform: Platform) -> Path:
        return self.BROWSER_DATA_DIR / platform.value

    async def _ensure_browser(self, headless: bool = True):
        if self._browser is None:
            from playwright.async_api import async_playwright

            self._playwright = await async_playwright().start()

            # Check if CDP mode is enabled and Chrome is available
            cdp_enabled = getattr(self.settings, "playwright_cdp_mode", False)
            chrome_path = self._find_chrome()

            if cdp_enabled and chrome_path:
                logger.info(f"CDP mode enabled, Chrome found at: {chrome_path}")
                self._browser = await self._launch_cdp_browser(chrome_path)
            else:
                if cdp_enabled and not chrome_path:
                    logger.warning(
                        "CDP mode enabled but Chrome not found, falling back to standard mode"
                    )
                self._browser = await self._playwright.chromium.launch(
                    headless=headless,
                    channel="chrome",
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--disable-infobars",
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-web-security",
                        "--disable-features=IsolateOrigins,site-per-process",
                    ],
                )
                logger.info("Browser launched with Chrome channel")

    def _find_chrome(self) -> Optional[str]:
        """Find Chrome executable path."""
        chrome_paths = [
            "/usr/bin/google-chrome-stable",
            "/usr/bin/google-chrome",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
            "/snap/bin/chromium",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
        ]

        for path in chrome_paths:
            if Path(path).exists():
                logger.info(f"Chrome found at: {path}")
                return path

        # Try to find using `which` command
        try:
            import subprocess

            for cmd in ["google-chrome-stable", "google-chrome", "chromium", "chromium-browser"]:
                result = subprocess.run(["which", cmd], capture_output=True, text=True)
                if result.returncode == 0:
                    chrome_path = result.stdout.strip()
                    if chrome_path:
                        logger.info(f"Chrome found via 'which {cmd}': {chrome_path}")
                        return chrome_path
        except Exception:
            pass

        logger.warning("Chrome not found in any known location")
        return None

    async def _launch_cdp_browser(self, chrome_path: str):
        """Launch Chrome with CDP for better anti-detection."""
        import socket
        import subprocess

        port = getattr(self.settings, "playwright_cdp_port", 9222)

        # Find available port
        while True:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect(("127.0.0.1", port))
                port += 1
            except ConnectionRefusedError:
                break

        logger.info(f"Starting Chrome with CDP on port {port}")
        logger.info(f"Chrome command: {chrome_path}")

        user_data_dir = Path(self.settings.browser_data_dir) / "chrome_cdp"
        user_data_dir.mkdir(parents=True, exist_ok=True)

        chrome_cmd = [
            chrome_path,
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
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ]

        self._chrome_process = subprocess.Popen(
            chrome_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Wait for Chrome to start with retry
        await asyncio.sleep(3)

        # Check if process is still running or exited with "existing session" message
        if self._chrome_process.poll() is not None:
            stdout, stderr = self._chrome_process.communicate()
            stdout_str = stdout.decode() if stdout else ""
            stderr_str = stderr.decode() if stderr else ""

            # If Chrome says it's opening in existing session, that's OK
            if "现有的浏览器会话" in stdout_str or "existing browser" in stdout_str.lower():
                logger.info("Chrome opened in existing session, will try to connect to port...")
            else:
                logger.error(f"Chrome process exited with code {self._chrome_process.returncode}")
                logger.error(f"Stdout: {stdout_str[:500]}")
                logger.error(f"Stderr: {stderr_str[:500]}")
                raise RuntimeError("Chrome process failed to start")

        # Try to connect with timeout
        max_retries = 15
        for i in range(max_retries):
            try:
                import socket

                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(2)
                    s.connect(("127.0.0.1", port))
                logger.info(f"Chrome is listening on port {port}")
                break
            except (ConnectionRefusedError, socket.timeout):
                await asyncio.sleep(1)
                if i == max_retries - 1:
                    raise RuntimeError(f"Chrome did not start listening on port {port}")
                continue

        cdp_url = f"http://127.0.0.1:{port}"
        logger.info(f"Connecting to Chrome CDP: {cdp_url}")

        browser = await self._playwright.chromium.connect_over_cdp(cdp_url)
        logger.info("Connected to Chrome via CDP")

        return browser

    async def _load_cookies(self, platform: Platform, context) -> bool:
        cookie_file = self._get_cookie_file(platform)
        if cookie_file.exists():
            try:
                with open(cookie_file, "r", encoding="utf-8") as f:
                    cookies = json.load(f)
                if cookies:
                    await context.add_cookies(cookies)
                    logger.info(f"Loaded {len(cookies)} cookies for {platform.value}")
                    return True
            except Exception as e:
                logger.warning(f"Failed to load cookies for {platform.value}: {e}")
        return False

    async def _save_cookies(self, platform: Platform, context) -> bool:
        try:
            cookies = await context.cookies()
            cookie_file = self._get_cookie_file(platform)
            with open(cookie_file, "w", encoding="utf-8") as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved {len(cookies)} cookies for {platform.value}")
            if platform not in self._states:
                self._states[platform] = LoginState(platform=platform)
            self._states[platform].cookies = cookies
            return True
        except Exception as e:
            logger.error(f"Failed to save cookies for {platform.value}: {e}")
            return False

    async def _inject_stealth_scripts(self, context):
        if STEALTH_JS_PATH.exists():
            try:
                await context.add_init_script(path=str(STEALTH_JS_PATH))
                logger.info(f"Injected stealth.min.js")
            except Exception as e:
                logger.warning(f"Failed to inject stealth.js: {e}")

        anti_detection_js = """
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
            configurable: true
        });
        if (!window.navigator.chrome) {
            window.navigator.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };
        }
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5],
            configurable: true
        });
        Object.defineProperty(navigator, 'languages', {
            get: () => ['zh-CN', 'zh', 'en'],
            configurable: true
        });
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
        """
        await context.add_init_script(anti_detection_js)
        logger.info("Injected anti-detection scripts")

    async def get_context(
        self,
        platform: Platform,
        headless: Optional[bool] = None,
        use_persistent: bool = True,
    ):
        # Use system-wide setting if not explicitly provided
        if headless is None:
            headless = self.settings.playwright_headless

        await self._ensure_browser(headless=headless)

        if platform in self._contexts:
            return self._contexts[platform], self._pages[platform]

        assert self._browser is not None
        context = await self._browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
        )

        await self._inject_stealth_scripts(context)
        await self._load_cookies(platform, context)

        page = await context.new_page()
        page.set_default_timeout(60000)

        self._contexts[platform] = context
        self._pages[platform] = page
        logger.info(f"Created browser context for {platform.value}")

        self._setup_cookie_auto_save(platform, context, page)

        return context, page

    def _setup_cookie_auto_save(self, platform: Platform, context, page):
        import threading

        self._last_cookie_save = {}
        self._cookie_save_lock = threading.Lock()

        async def save_cookies_async():
            try:
                cookies = await context.cookies()
                cookie_file = self._get_cookie_file(platform)
                with open(cookie_file, "w", encoding="utf-8") as f:
                    json.dump(cookies, f, ensure_ascii=False, indent=2)
                logger.debug(f"Auto-saved {len(cookies)} cookies for {platform.value}")
            except Exception as e:
                logger.warning(f"Failed to auto-save cookies: {e}")

        def on_response(response):
            try:
                set_cookie = response.headers.get("set-cookie")
                if set_cookie:
                    asyncio.create_task(save_cookies_async())
            except Exception:
                pass

        page.on("response", on_response)
        logger.info(f"Cookie auto-save enabled for {platform.value}")

    async def navigate_via_baidu(self, page) -> bool:
        try:
            logger.info("Navigating via Baidu homepage to avoid CAPTCHA...")

            await page.goto("https://www.baidu.com/", wait_until="domcontentloaded")
            await asyncio.sleep(2)

            tieba_selectors = [
                'a[href="http://tieba.baidu.com/"]',
                'a[href="https://tieba.baidu.com/"]',
                'a.mnav:has-text("贴吧")',
                "text=贴吧",
            ]

            tieba_link = None
            for selector in tieba_selectors:
                try:
                    tieba_link = await page.wait_for_selector(selector, timeout=5000)
                    if tieba_link:
                        break
                except Exception:
                    continue

            if tieba_link:
                target_attr = await tieba_link.get_attribute("target")
                if target_attr == "_blank":
                    async with page.context.expect_page() as new_page_info:
                        await tieba_link.click()
                    new_page = await new_page_info.value
                    await new_page.wait_for_load_state("domcontentloaded")
                    await page.close()
                    self._pages[Platform.TIEBA] = new_page
                    logger.info(f"Navigated to Tieba via Baidu homepage")
                    return True
                else:
                    async with page.expect_navigation(wait_until="domcontentloaded"):
                        await tieba_link.click()
                    logger.info(f"Navigated to Tieba via Baidu homepage")
                    return True
            else:
                logger.warning("Tieba link not found, direct navigation")
                await page.goto("https://tieba.baidu.com/", wait_until="domcontentloaded")
                return True

        except Exception as e:
            logger.error(f"Failed to navigate via Baidu: {e}")
            await page.goto("https://tieba.baidu.com/", wait_until="domcontentloaded")
            return False

    async def get_logged_in_context(
        self,
        platform: Platform,
        headless: Optional[bool] = None,
        auto_login: bool = True,
        login_timeout: int = 300000,
    ):
        context, page = await self.get_context(platform, headless=headless)
        handler = self._handlers.get(platform)

        if not handler:
            raise ValueError(f"No handler registered for platform: {platform}")

        if platform == Platform.TIEBA:
            await self.navigate_via_baidu(page)
            page = self._pages.get(platform, page)
        else:
            await page.goto(handler.get_home_url(), wait_until="networkidle")

        if await handler.check_login_status(page):
            logger.info(f"Already logged in to {platform.value}")
            if platform not in self._states:
                self._states[platform] = LoginState(platform=platform, is_logged_in=True)
            else:
                self._states[platform].is_logged_in = True
            return context, page

        if not auto_login:
            raise RuntimeError(f"Not logged in to {platform.value}")

        logger.info(f"Not logged in to {platform.value}, triggering login flow...")

        if platform == Platform.TIEBA:
            logger.info("Clicking login button to enter login page...")
            try:
                login_selectors = [
                    'a[href*="passport"]',
                    ".login_btn",
                    'a:has-text("登录")',
                ]
                for selector in login_selectors:
                    try:
                        login_btn = await page.wait_for_selector(selector, timeout=3000)
                        if login_btn:
                            await login_btn.click()
                            await asyncio.sleep(2)
                            logger.info(f"Navigated to login page: {page.url}")
                            break
                    except Exception:
                        continue
            except Exception as e:
                logger.warning(f"Could not click login button: {e}")

        logger.info("Waiting for user to complete login...")
        if await handler.wait_for_login(page, timeout=login_timeout):
            await self._save_cookies(platform, context)
            if platform not in self._states:
                self._states[platform] = LoginState(platform=platform, is_logged_in=True)
            else:
                self._states[platform].is_logged_in = True
            return context, page

        raise RuntimeError(f"Login failed for {platform.value}")

    async def is_logged_in(self, platform: Platform) -> bool:
        state = self._states.get(platform)
        if state and state.is_logged_in:
            return True
        if platform in self._pages:
            page = self._pages[platform]
            handler = self._handlers.get(platform)
            if handler:
                return await handler.check_login_status(page)
        return False

    async def verify_login(self, platform: Platform) -> bool:
        context, page = await self.get_context(platform)
        handler = self._handlers.get(platform)
        if not handler:
            return False
        await page.goto(handler.get_home_url(), wait_until="networkidle")
        is_logged = await handler.check_login_status(page)
        if platform not in self._states:
            self._states[platform] = LoginState(platform=platform, is_logged_in=is_logged)
        else:
            self._states[platform].is_logged_in = is_logged
        return is_logged

    async def logout(self, platform: Platform) -> bool:
        try:
            if platform in self._contexts:
                await self._contexts[platform].close()
                del self._contexts[platform]
                del self._pages[platform]

            cookie_file = self._get_cookie_file(platform)
            if cookie_file.exists():
                cookie_file.unlink()

            if platform in self._states:
                del self._states[platform]

            logger.info(f"Logged out from {platform.value}")
            return True
        except Exception as e:
            logger.error(f"Failed to logout from {platform.value}: {e}")
            return False

    async def close(self):
        try:
            for platform in list(self._contexts.keys()):
                if self._pages.get(platform):
                    await self._pages[platform].close()
                if self._contexts.get(platform):
                    await self._contexts[platform].close()

            if self._browser:
                await self._browser.close()

            if self._playwright:
                await self._playwright.stop()

            self._contexts.clear()
            self._pages.clear()
            self._browser = None
            self._playwright = None
            logger.info("LoginManager closed all resources")
        except Exception as e:
            logger.error(f"Error closing LoginManager: {e}")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


_login_manager_instance: Optional[LoginManager] = None


def get_login_manager() -> LoginManager:
    global _login_manager_instance
    if _login_manager_instance is None:
        _login_manager_instance = LoginManager()
    return _login_manager_instance
