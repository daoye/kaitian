from __future__ import annotations

import asyncio
import shutil
import logging
import subprocess
import time
from collections.abc import Iterable
from typing import Any
import importlib
from urllib.parse import urlparse

from core.models import Session

from .exceptions import (
    BrowserContextError,
    BrowserCookieError,
    BrowserCdpError,
    BrowserLaunchError,
    BrowserPageError,
    BrowserSessionError,
)
from .retry import retry
from .types import BrowserContextOptions, BrowserLaunchOptions, Cookie, RouteRule

logger = logging.getLogger("browser")


def _resolve_system_chrome_path() -> str | None:
    """查找系统 Chrome 路径，支持 Windows、Linux 和 macOS."""
    import os
    import platform

    system = platform.system()

    # Windows 常见路径
    if system == "Windows":
        windows_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%PROGRAMFILES(x86)%\Google\Chrome\Application\chrome.exe"),
        ]
        for path in windows_paths:
            if os.path.exists(path):
                return path

    # 通用命令查找
    for candidate in (
        "google-chrome",
        "google-chrome-stable",
        "chromium",
        "chromium-browser",
        "chrome",
    ):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved

    return None


class ManagedCdpSession:
    """托管 CDP 会话，用于发送原生 Chrome DevTools Protocol 命令."""

    def __init__(self, session: Any) -> None:
        self._session = session
        self._closed = False

    async def send(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """发送 CDP 命令.

        Args:
            method: CDP 方法名，如 "Runtime.evaluate", "Network.enable" 等
            params: 方法参数

        Returns:
            CDP 命令返回结果

        Raises:
            BrowserCdpError: 发送命令失败
        """
        if self._closed:
            raise BrowserCdpError("CDP session is closed")
        try:
            return await self._session.send(method, params or {})
        except Exception as exc:
            raise BrowserCdpError(
                f"failed to send CDP command: {method}",
                details={"method": method, "params": params, "cause": str(exc)},
            ) from exc

    async def detach(self) -> None:
        """分离 CDP 会话."""
        if self._closed:
            return
        self._closed = True
        try:
            await self._session.detach()
        except Exception:
            pass

    async def close(self) -> None:
        """关闭 CDP 会话（detach 的别名）."""
        await self.detach()

    @property
    def raw(self) -> Any:
        """获取原始 CDP 会话对象."""
        return self._session


class ManagedPage:
    """托管页面，支持 CDP 操作."""

    def __init__(self, page: Any, context: "ManagedBrowserContext") -> None:
        self._page = page
        self._context = context
        self._closed = False

    def __getattr__(self, name: str) -> Any:
        """委托未定义的方法到原始 page 对象."""
        return getattr(self._page, name)

    @property
    def raw(self) -> Any:
        """获取原始页面对象."""
        return self._page

    async def new_cdp_session(self) -> ManagedCdpSession:
        """创建页面级别的 CDP 会话.

        Returns:
            ManagedCdpSession 实例

        Raises:
            BrowserCdpError: 创建会话失败
        """
        if self._closed:
            raise BrowserPageError("page is closed")
        try:
            session = await self._context.raw.new_cdp_session(self._page)
            return ManagedCdpSession(session)
        except Exception as exc:
            raise BrowserCdpError(
                "failed to create CDP session for page", details={"cause": str(exc)}
            ) from exc

    async def close(self) -> None:
        """关闭页面."""
        if self._closed:
            return
        self._closed = True
        await self._page.close()

    async def __aenter__(self) -> "ManagedPage":
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.close()


class ManagedBrowserContext:
    def __init__(
        self,
        context: Any,
        options: BrowserContextOptions,
        route_rules: list[RouteRule] | None = None,
        stealth_hook: Any = None,
        owned: bool = True,
    ) -> None:
        self._context = context
        self._options = options
        self._route_rules = route_rules or []
        self._stealth_hook = stealth_hook
        self._closed = False
        self._owned = owned  # 是否拥有底层上下文（借用的上下文不应关闭底层）

    @property
    def raw(self) -> Any:
        return self._context

    async def initialize(self) -> "ManagedBrowserContext":
        if self._options.default_timeout_ms is not None:
            self._context.set_default_timeout(self._options.default_timeout_ms)
        if self._options.navigation_timeout_ms is not None:
            self._context.set_default_navigation_timeout(self._options.navigation_timeout_ms)
        for rule in self._route_rules:
            await self._context.route(rule.pattern, rule.handler)
        if self._stealth_hook is not None:
            await self._stealth_hook(self._context)
        return self

    async def new_page(self) -> ManagedPage:
        """创建新页面.

        Returns:
            ManagedPage 实例，支持 CDP 操作

        Raises:
            BrowserContextError: 创建页面失败
        """
        try:
            raw_page = await asyncio.wait_for(
                self._context.new_page(),
                timeout=self._options.page_creation_timeout_ms / 1000,
            )
            return ManagedPage(raw_page, self)
        except asyncio.TimeoutError as exc:
            raise BrowserContextError(
                "page creation timed out",
                details={"timeout_ms": self._options.page_creation_timeout_ms},
            ) from exc
        except Exception as exc:
            raise BrowserContextError("failed to create page", details={"cause": str(exc)}) from exc

    async def new_cdp_session(self, page: ManagedPage | None = None) -> ManagedCdpSession:
        """创建 CDP 会话.

        Args:
            page: 如果指定，创建页面级别的 CDP 会话；否则创建浏览器上下文级别的会话

        Returns:
            ManagedCdpSession 实例

        Raises:
            BrowserCdpError: 创建会话失败
        """
        if self._closed:
            raise BrowserContextError("context is closed")
        try:
            if page is not None:
                session = await self._context.new_cdp_session(page.raw)
            else:
                session = await self._context.new_cdp_session()
            return ManagedCdpSession(session)
        except Exception as exc:
            raise BrowserCdpError(
                "failed to create CDP session",
                details={"has_page": page is not None, "cause": str(exc)},
            ) from exc

    async def add_cookies(self, cookies: list[dict[str, Any]]) -> None:
        try:
            await self._context.add_cookies(cookies)
        except Exception as exc:
            raise BrowserCookieError("failed to add cookies", details={"cause": str(exc)}) from exc

    async def cookies(self) -> list[dict[str, Any]]:
        try:
            return await self._context.cookies()
        except Exception as exc:
            raise BrowserCookieError("failed to get cookies", details={"cause": str(exc)}) from exc

    async def storage_state(self, path: str | None = None) -> dict[str, Any]:
        try:
            if path is None:
                return await self._context.storage_state()
            return await self._context.storage_state(path=path)
        except Exception as exc:
            raise BrowserContextError(
                "failed to export storage state", details={"cause": str(exc)}
            ) from exc

    async def set_extra_http_headers(self, headers: dict[str, str]) -> None:
        await self._context.set_extra_http_headers(headers)

    def _mark_closed(self) -> None:
        """标记为已关闭（不关闭底层上下文，用于借用的上下文）."""
        self._closed = True

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        # 只有拥有的上下文才关闭底层 Playwright 上下文
        if self._owned:
            await self._context.close()

    async def __aenter__(self) -> "ManagedBrowserContext":
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.close()


class BrowserManager:
    def __init__(
        self,
        launch_options: BrowserLaunchOptions | None = None,
        playwright_factory: Any = None,
        stealth_hook: Any = None,
    ) -> None:
        self._launch_options = launch_options or BrowserLaunchOptions()
        self._playwright_factory = playwright_factory
        self._stealth_hook = stealth_hook
        self._playwright = None
        self._browser = None
        self._contexts: dict[str, ManagedBrowserContext] = {}  # 复用键管理的上下文
        self._all_contexts: list[ManagedBrowserContext] = []  # 所有创建的上下文（用于清理）
        self._default_context: ManagedBrowserContext | None = None
        self._route_rules: list[RouteRule] = []
        self._started = False
        self._context_lock = asyncio.Lock()  # 保护上下文创建的锁

        # 运行时状态
        self._owns_browser_process: bool = False  # 是否拥有 Chrome 进程（需要负责关闭）
        self._attached_default_context: ManagedBrowserContext | None = None
        self._chrome_process: subprocess.Popen | None = None  # 自己启动的 Chrome 进程

    async def start(self) -> "BrowserManager":
        """启动浏览器，带重试机制."""
        return await self._start_with_retry()

    @retry(max_attempts=3, delay_ms=500, backoff=2.0, exceptions=(BrowserLaunchError,))
    async def _start_with_retry(self) -> "BrowserManager":
        """带重试的启动逻辑，支持 launch 和 connect_cdp 两种模式."""
        if self._started:
            logger.debug("browser.start.skipped", extra={"reason": "already_started"})
            return self
        try:
            logger.info(
                "browser.start.begin",
                extra={
                    "engine": self._launch_options.engine,
                    "enable_cdp": self._launch_options.enable_cdp,
                    "headless": self._launch_options.headless,
                },
            )
            factory = self._playwright_factory
            if factory is None:
                async_api = importlib.import_module("playwright.async_api")
                factory = getattr(async_api, "async_playwright")
            runner = factory()
            self._playwright = await runner.start()

            if self._launch_options.enable_cdp:
                await self._start_cdp_mode()
            else:
                await self._start_launch_mode()

            self._started = True
            logger.info(
                "browser.start.success",
                extra={
                    "engine": self._launch_options.engine,
                    "enable_cdp": self._launch_options.enable_cdp,
                    "owns_process": self._owns_browser_process,
                },
            )
            return self
        except Exception as exc:
            logger.error(
                "browser.start.failed",
                extra={
                    "engine": self._launch_options.engine,
                    "enable_cdp": self._launch_options.enable_cdp,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
            )
            raise BrowserLaunchError(
                "failed to start browser",
                details={"enable_cdp": self._launch_options.enable_cdp, "cause": str(exc)},
            ) from exc

    async def _start_launch_mode(self) -> None:
        """启动模式：直接启动浏览器（非 CDP 模式）."""
        engine = getattr(self._playwright, self._launch_options.engine)
        args = self._launch_options.launch_args.copy()
        launch_kwargs = {
            "headless": self._launch_options.headless,
            "slow_mo": self._launch_options.slow_mo_ms,
            "proxy": self._launch_options.proxy,
            "args": args,
            "timeout": self._launch_options.timeout_ms,
        }
        if self._launch_options.engine == "chromium":
            system_chrome = _resolve_system_chrome_path()
            if system_chrome is not None:
                launch_kwargs["executable_path"] = system_chrome
            else:
                launch_kwargs["channel"] = "chrome"
        self._browser = await engine.launch(**launch_kwargs)
        self._owns_browser_process = True

    async def _start_cdp_mode(self) -> None:
        """CDP 模式：智能检测并连接 CDP 浏览器.

        先尝试连接到已有的 CDP 服务端，如果失败则自动启动一个服务端并连接。
        """
        import subprocess
        import time

        if self._launch_options.engine != "chromium":
            raise BrowserLaunchError(
                "connect_cdp mode only supports chromium engine",
                details={"engine": self._launch_options.engine},
            )

        cdp_url = self._launch_options.cdp_endpoint_url
        port = 9222  # 默认端口

        # 如果提供了具体的端点 URL，解析端口
        if cdp_url:
            try:
                from urllib.parse import urlparse

                parsed = urlparse(cdp_url)
                if parsed.port:
                    port = parsed.port
            except Exception:
                pass
        else:
            cdp_url = f"http://localhost:{port}"

        # 尝试连接 CDP 端口
        logger.info("browser.cdp.connect.attempt", extra={"endpoint": cdp_url})
        connected = await self._try_connect_cdp(cdp_url)

        if not connected:
            logger.info("browser.cdp.connect.failed_starting_new", extra={"port": port})
            # 启动新的 Chrome 进程
            await self._start_chrome_with_cdp(port)
            # 等待 Chrome 就绪
            await self._wait_for_cdp_ready(port)
            # 重新连接
            cdp_url = f"http://localhost:{port}"
            connected = await self._try_connect_cdp(cdp_url)

            if not connected:
                raise BrowserLaunchError(
                    "failed to connect to CDP after starting new browser",
                    details={"endpoint": cdp_url},
                )

            # 标记为我们自己启动的进程，需要负责关闭
            self._owns_browser_process = True

    async def _try_connect_cdp(self, endpoint_url: str) -> bool:
        """尝试连接 CDP 端点，返回是否成功."""
        try:
            self._browser = await self._playwright.chromium.connect_over_cdp(
                endpoint_url,
                headers=self._launch_options.cdp_headers or None,
                slow_mo=self._launch_options.slow_mo_ms,
                timeout=self._launch_options.timeout_ms,
            )
            logger.info("browser.cdp.connect.success", extra={"endpoint": endpoint_url})
            return True
        except Exception as exc:
            logger.debug(
                "browser.cdp.connect.failed", extra={"endpoint": endpoint_url, "error": str(exc)}
            )
            return False

    async def _start_chrome_with_cdp(self, port: int) -> None:
        """启动带有 CDP 端口的 Chrome 进程.

        Raises:
            BrowserLaunchError: 如果找不到系统 Chrome 或启动失败
        """
        import os

        system_chrome = _resolve_system_chrome_path()

        if not system_chrome:
            raise BrowserLaunchError(
                "无法找到 Google Chrome 浏览器",
                details={
                    "hint": "请先安装 Google Chrome",
                    "windows": "https://www.google.com/chrome/",
                    "linux": "sudo apt install google-chrome-stable 或 sudo yum install google-chrome-stable",
                    "macos": "brew install --cask google-chrome",
                },
            )

        # 使用系统 Chrome
        logger.info("browser.cdp.using_system_chrome", extra={"path": system_chrome})
        args = [
            f"--remote-debugging-port={port}",
            "--no-first-run",
            "--no-default-browser-check",
        ]

        if self._launch_options.headless:
            args.append("--headless=new")

        # 添加用户指定的额外参数
        args.extend(self._launch_options.launch_args)

        logger.info(
            "browser.cdp.launch.starting", extra={"executable": system_chrome, "port": port}
        )

        try:
            # Windows 上不使用 start_new_session
            kwargs = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
            if os.name != "nt":
                kwargs["start_new_session"] = True

            process = subprocess.Popen([system_chrome] + args, **kwargs)

            # 存储进程以便后续关闭
            self._chrome_process = process
            logger.info("browser.cdp.launch.started", extra={"pid": process.pid, "port": port})
        except Exception as exc:
            raise BrowserLaunchError(
                "failed to start Chrome with CDP",
                details={"executable": system_chrome, "error": str(exc)},
            ) from exc

    async def _wait_for_cdp_ready(self, port: int, timeout_ms: int = 30000) -> None:
        """等待 CDP 端口就绪."""
        import aiohttp

        start_time = time.time()
        endpoint = f"http://localhost:{port}/json/version"

        logger.debug("browser.cdp.waiting_ready", extra={"endpoint": endpoint})

        while (time.time() - start_time) * 1000 < timeout_ms:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(endpoint, timeout=1) as response:
                        if response.status == 200:
                            logger.info("browser.cdp.ready", extra={"port": port})
                            return
            except Exception:
                pass
            await asyncio.sleep(0.5)

        raise BrowserLaunchError(
            "timeout waiting for CDP to be ready", details={"port": port, "timeout_ms": timeout_ms}
        )

    async def new_context(
        self, options: BrowserContextOptions | None = None
    ) -> ManagedBrowserContext:
        await self.start()
        if self._browser is None:
            raise BrowserLaunchError("browser is not available after startup")
        context_options = options or BrowserContextOptions()

        # 使用锁保护复用键的检查和创建，防止并发竞态
        if context_options.reuse_key:
            async with self._context_lock:
                if context_options.reuse_key in self._contexts:
                    logger.debug(
                        "browser.context.reuse",
                        extra={
                            "reuse_key": context_options.reuse_key,
                        },
                    )
                    return self._contexts[context_options.reuse_key]
                return await self._create_context(context_options)
        else:
            # 无复用键时也需要检查限制
            async with self._context_lock:
                return await self._create_context(context_options)

    async def _create_context(
        self, context_options: BrowserContextOptions
    ) -> ManagedBrowserContext:
        """实际创建上下文的逻辑（必须在持有锁的情况下调用）."""
        # 清理已关闭的上下文
        self._all_contexts = [ctx for ctx in self._all_contexts if not ctx._closed]
        # 检查上下文数量限制
        if len(self._all_contexts) >= self._launch_options.max_contexts:
            raise BrowserContextError(
                f"max contexts limit reached: {self._launch_options.max_contexts}",
                details={
                    "current": len(self._all_contexts),
                    "limit": self._launch_options.max_contexts,
                },
            )
        logger.info(
            "browser.context.create.begin",
            extra={
                "reuse_key": context_options.reuse_key,
                "base_url": context_options.base_url,
            },
        )
        if self._browser is None:
            raise BrowserLaunchError("browser is not available after startup")
        try:
            raw_context = await self._browser.new_context(
                base_url=context_options.base_url,
                viewport=context_options.viewport,
                user_agent=context_options.user_agent,
                locale=context_options.locale,
                timezone_id=context_options.timezone_id,
                storage_state=context_options.storage_state,
                extra_http_headers=context_options.extra_http_headers or None,
            )
        except FileNotFoundError as e:
            logger.error(
                "browser.context.create.failed",
                extra={
                    "error_type": "FileNotFoundError",
                    "storage_state": context_options.storage_state,
                },
            )
            raise BrowserContextError(
                f"storage_state file not found: {e}",
                details={"path": context_options.storage_state},
            ) from e
        except Exception as e:
            logger.error(
                "browser.context.create.failed",
                extra={
                    "error_type": type(e).__name__,
                    "error": str(e),
                },
            )
            raise BrowserContextError(
                f"failed to create browser context: {e}", details={"cause": str(e)}
            ) from e
        logger.info(
            "browser.context.create.success",
            extra={
                "reuse_key": context_options.reuse_key,
            },
        )
        managed = await ManagedBrowserContext(
            raw_context,
            context_options,
            route_rules=self._route_rules,
            stealth_hook=self._stealth_hook,
        ).initialize()
        self._all_contexts.append(managed)
        if context_options.reuse_key:
            self._contexts[context_options.reuse_key] = managed
        return managed

    async def get_default_context(self) -> ManagedBrowserContext:
        if self._default_context is None:
            self._default_context = await self.new_context(BrowserContextOptions())
        return self._default_context

    async def new_page(self) -> Any:
        context = await self.get_default_context()
        return await context.new_page()

    async def add_route(self, pattern: str, handler: Any) -> None:
        self._route_rules.append(RouteRule(pattern=pattern, handler=handler))

    async def get_cookies(self) -> list[dict[str, Any]]:
        context = await self.get_default_context()
        return await context.cookies()

    async def set_cookies(self, cookies: Iterable[dict[str, Any]]) -> None:
        context = await self.get_default_context()
        await context.add_cookies(list(cookies))

    async def export_storage_state(self, path: str | None = None) -> dict[str, Any]:
        context = await self.get_default_context()
        return await context.storage_state(path=path)

    async def import_storage_state(
        self, storage_state: str | dict[str, Any]
    ) -> ManagedBrowserContext:
        return await self.new_context(BrowserContextOptions(storage_state=storage_state))

    async def apply_session(self, session: Session, base_url: str | None = None) -> None:
        cookies = self._session_to_cookies(session, base_url=base_url)
        await self.set_cookies(cookies)
        headers = {key: value for key, value in session.headers.items() if isinstance(value, str)}
        if headers:
            context = await self.get_default_context()
            await context.set_extra_http_headers(headers)

    def _session_to_cookies(
        self, session: Session, base_url: str | None = None
    ) -> list[dict[str, Any]]:
        domain = self._infer_cookie_domain(session, base_url)
        cookies: list[dict[str, Any]] = []
        for name, value in session.cookies.items():
            cookie = Cookie(name=name, value=value, domain=domain)
            cookies.append(cookie.to_playwright())
        return cookies

    def _infer_cookie_domain(self, session: Session, base_url: str | None = None) -> str:
        candidate = (
            session.metadata.get("cookie_domain") if isinstance(session.metadata, dict) else None
        )
        if isinstance(candidate, str) and candidate:
            return candidate
        if isinstance(base_url, str) and base_url:
            parsed = urlparse(base_url)
            if parsed.hostname:
                return parsed.hostname if parsed.hostname.startswith(".") else f".{parsed.hostname}"
        site = session.site.strip()
        if "." in site:
            return site if site.startswith(".") else f".{site}"
        raise BrowserSessionError("unable to infer cookie domain", details={"site": session.site})

    async def new_browser_cdp_session(self) -> ManagedCdpSession:
        """创建浏览器级别的 CDP 会话.

        Returns:
            ManagedCdpSession 实例，可以发送浏览器级别的 CDP 命令

        Raises:
            BrowserCdpError: 创建会话失败
            BrowserLaunchError: 浏览器未启动

        Example:
            session = await browser_manager.new_browser_cdp_session()
            result = await session.send("Browser.getVersion")
            await session.detach()
        """
        if not self._started:
            raise BrowserLaunchError("browser is not started")
        if self._browser is None:
            raise BrowserLaunchError("browser is not available")
        try:
            session = await self._browser.new_browser_cdp_session()
            return ManagedCdpSession(session)
        except Exception as exc:
            raise BrowserCdpError(
                "failed to create browser CDP session", details={"cause": str(exc)}
            ) from exc

    async def close(self) -> None:
        if not self._started:
            logger.debug("browser.close.skipped", extra={"reason": "not_started"})
            return
        logger.info(
            "browser.close.begin",
            extra={
                "context_count": len(self._all_contexts),
                "owns_process": self._owns_browser_process,
            },
        )
        try:
            # 关闭默认上下文
            if self._default_context is not None:
                await self._default_context.close()
                self._default_context = None
            # 关闭附加的默认上下文（借用的，不关闭底层）
            if self._attached_default_context is not None:
                # 只标记关闭，不关闭底层 Playwright 上下文
                self._attached_default_context._mark_closed()
                self._attached_default_context = None
            # 关闭所有追踪的上下文（避免重复关闭）
            closed_ids = set()
            for context in self._all_contexts:
                if id(context) not in closed_ids:
                    await context.close()
                    closed_ids.add(id(context))
            self._all_contexts.clear()
            # 清空复用字典
            self._contexts.clear()
            # 关闭浏览器连接
            if self._browser is not None:
                await self._browser.close()
                self._browser = None
            # 如果自己启动了 Chrome 进程，关闭它
            if self._chrome_process is not None and self._owns_browser_process:
                logger.info(
                    "browser.chrome_process.terminating", extra={"pid": self._chrome_process.pid}
                )
                try:
                    self._chrome_process.terminate()
                    try:
                        self._chrome_process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        self._chrome_process.kill()
                        self._chrome_process.wait()
                    logger.info(
                        "browser.chrome_process.terminated", extra={"pid": self._chrome_process.pid}
                    )
                except Exception as e:
                    logger.warning(
                        "browser.chrome_process.terminate_failed", extra={"error": str(e)}
                    )
                finally:
                    self._chrome_process = None
            if self._playwright is not None:
                await self._playwright.stop()
                self._playwright = None
            self._started = False
            logger.info("browser.close.success")
        except Exception as e:
            logger.error(
                "browser.close.failed",
                extra={
                    "error_type": type(e).__name__,
                    "error": str(e),
                },
            )
            raise

    async def __aenter__(self) -> "BrowserManager":
        return await self.start()

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.close()
