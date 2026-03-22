from __future__ import annotations

import asyncio
import shutil
import logging
from collections.abc import Iterable
from typing import Any
import importlib
from urllib.parse import urlparse

from core.models import Session

from .exceptions import (
    BrowserContextError,
    BrowserCookieError,
    BrowserLaunchError,
    BrowserSessionError,
)
from .retry import retry
from .types import BrowserContextOptions, BrowserLaunchOptions, Cookie, RouteRule

logger = logging.getLogger("browser")


def _resolve_system_chrome_path() -> str | None:
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


class ManagedBrowserContext:
    def __init__(
        self,
        context: Any,
        options: BrowserContextOptions,
        route_rules: list[RouteRule] | None = None,
        stealth_hook: Any = None,
    ) -> None:
        self._context = context
        self._options = options
        self._route_rules = route_rules or []
        self._stealth_hook = stealth_hook
        self._closed = False

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

    async def new_page(self) -> Any:
        try:
            return await asyncio.wait_for(
                self._context.new_page(),
                timeout=self._options.page_creation_timeout_ms / 1000,
            )
        except asyncio.TimeoutError as exc:
            raise BrowserContextError(
                "page creation timed out",
                details={"timeout_ms": self._options.page_creation_timeout_ms},
            ) from exc
        except Exception as exc:
            raise BrowserContextError("failed to create page", details={"cause": str(exc)}) from exc

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

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
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

    async def start(self) -> "BrowserManager":
        """启动浏览器，带重试机制."""
        return await self._start_with_retry()

    @retry(max_attempts=3, delay_ms=500, backoff=2.0, exceptions=(BrowserLaunchError,))
    async def _start_with_retry(self) -> "BrowserManager":
        """带重试的启动逻辑."""
        if self._started:
            logger.debug("browser.start.skipped", extra={"reason": "already_started"})
            return self
        try:
            logger.info(
                "browser.start.begin",
                extra={
                    "engine": self._launch_options.engine,
                    "headless": self._launch_options.headless,
                },
            )
            factory = self._playwright_factory
            if factory is None:
                async_api = importlib.import_module("playwright.async_api")
                factory = getattr(async_api, "async_playwright")
            runner = factory()
            self._playwright = await runner.start()
            engine = getattr(self._playwright, self._launch_options.engine)
            args = self._launch_options.launch_args.copy()
            if self._launch_options.enable_cdc:
                args.append("--auto-open-devtools-for-tabs")
            if self._launch_options.cdp_port is not None:
                args.append(f"--remote-debugging-port={self._launch_options.cdp_port}")
            else:
                # 如果启用 CDC 但没有指定端口，使用默认端口 9222
                if self._launch_options.enable_cdc:
                    args.append("--remote-debugging-port=9222")
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
            self._browser = await engine.launch(
                **launch_kwargs,
            )
            self._started = True
            logger.info(
                "browser.start.success",
                extra={
                    "engine": self._launch_options.engine,
                    "headless": self._launch_options.headless,
                },
            )
            return self
        except Exception as exc:
            logger.error(
                "browser.start.failed",
                extra={
                    "engine": self._launch_options.engine,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
            )
            raise BrowserLaunchError(
                "failed to launch browser", details={"cause": str(exc)}
            ) from exc

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

    async def close(self) -> None:
        if not self._started:
            logger.debug("browser.close.skipped", extra={"reason": "not_started"})
            return
        logger.info(
            "browser.close.begin",
            extra={
                "context_count": len(self._all_contexts),
            },
        )
        try:
            # 关闭默认上下文
            if self._default_context is not None:
                await self._default_context.close()
                self._default_context = None
            # 关闭所有追踪的上下文（避免重复关闭）
            closed_ids = set()
            for context in self._all_contexts:
                if id(context) not in closed_ids:
                    await context.close()
                    closed_ids.add(id(context))
            self._all_contexts.clear()
            # 清空复用字典
            self._contexts.clear()
            # 关闭浏览器
            if self._browser is not None:
                await self._browser.close()
                self._browser = None
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
