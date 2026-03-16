from __future__ import annotations

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
from .types import BrowserContextOptions, BrowserLaunchOptions, Cookie, RouteRule


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
            return await self._context.new_page()
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
        self._contexts: dict[str, ManagedBrowserContext] = {}
        self._default_context: ManagedBrowserContext | None = None
        self._route_rules: list[RouteRule] = []
        self._started = False

    async def start(self) -> "BrowserManager":
        if self._started:
            return self
        try:
            factory = self._playwright_factory
            if factory is None:
                async_api = importlib.import_module("playwright.async_api")
                factory = getattr(async_api, "async_playwright")
            runner = factory()
            self._playwright = await runner.start()
            engine = getattr(self._playwright, self._launch_options.engine)
            self._browser = await engine.launch(
                headless=self._launch_options.headless,
                slow_mo=self._launch_options.slow_mo_ms,
                proxy=self._launch_options.proxy,
                args=self._launch_options.launch_args,
            )
            self._started = True
            return self
        except Exception as exc:
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
        if context_options.reuse_key and context_options.reuse_key in self._contexts:
            return self._contexts[context_options.reuse_key]
        raw_context = await self._browser.new_context(
            base_url=context_options.base_url,
            viewport=context_options.viewport,
            user_agent=context_options.user_agent,
            locale=context_options.locale,
            timezone_id=context_options.timezone_id,
            storage_state=context_options.storage_state,
            extra_http_headers=context_options.extra_http_headers or None,
        )
        managed = await ManagedBrowserContext(
            raw_context,
            context_options,
            route_rules=self._route_rules,
            stealth_hook=self._stealth_hook,
        ).initialize()
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
        if self._default_context is not None:
            await self._default_context.close()
            self._default_context = None
        for key, context in list(self._contexts.items()):
            await context.close()
            self._contexts.pop(key, None)
        if self._browser is not None:
            await self._browser.close()
            self._browser = None
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None
        self._started = False

    async def __aenter__(self) -> "BrowserManager":
        return await self.start()

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.close()
