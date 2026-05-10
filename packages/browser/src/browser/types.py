from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Literal, Protocol


CookieSameSite = Literal["Strict", "Lax", "None"]
BrowserEngine = Literal["chromium", "firefox", "webkit"]
ResourceType = Literal[
    "document",
    "stylesheet",
    "image",
    "media",
    "font",
    "script",
    "texttrack",
    "xhr",
    "fetch",
    "eventsource",
    "websocket",
    "manifest",
    "other",
]


@dataclass(slots=True)
class BrowserLaunchOptions:
    engine: BrowserEngine = "chromium"
    headless: bool = True
    timeout_ms: int = 30000
    page_timeout_ms: int = 10000
    max_contexts: int = 10
    slow_mo_ms: int = 0
    # 启用 CDP 模式：自动检测并连接，没有则自动启动
    enable_cdp: bool = False
    launch_args: list[str] = field(default_factory=list)
    proxy: dict[str, str] | None = None

    # CDP 端点 URL（可选，默认 http://localhost:9222）
    cdp_endpoint_url: str | None = None
    # CDP 端口（可选，默认 9222）
    remote_debugging_port: int | None = None
    cdp_headers: dict[str, str] = field(default_factory=dict)


ContextPreference = Literal["auto", "attached", "new"]


@dataclass(slots=True)
class BrowserContextOptions:
    reuse_key: str | None = None
    # 上下文偏好：auto（自动选择）、attached（使用已附加的默认上下文）、new（创建新上下文）
    context_preference: ContextPreference = "auto"
    base_url: str | None = None
    viewport: dict[str, int] | None = None
    user_agent: str | None = None
    locale: str | None = None
    timezone_id: str | None = None
    storage_state: str | dict[str, Any] | None = None
    extra_http_headers: dict[str, str] = field(default_factory=dict)
    default_timeout_ms: int | None = None
    navigation_timeout_ms: int | None = None
    page_creation_timeout_ms: int = 10000  # 页面创建超时（毫秒）


@dataclass(slots=True)
class Cookie:
    name: str
    value: str
    domain: str
    path: str = "/"
    expires: int | None = None
    http_only: bool = False
    secure: bool = False
    same_site: CookieSameSite | None = None

    def to_playwright(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": self.name,
            "value": self.value,
            "domain": self.domain,
            "path": self.path,
            "httpOnly": self.http_only,
            "secure": self.secure,
        }
        if self.expires is not None:
            payload["expires"] = self.expires
        if self.same_site is not None:
            payload["sameSite"] = self.same_site
        return payload

    @classmethod
    def from_playwright(cls, payload: dict[str, Any]) -> "Cookie":
        return cls(
            name=payload["name"],
            value=payload["value"],
            domain=payload["domain"],
            path=payload.get("path", "/"),
            expires=payload.get("expires"),
            http_only=payload.get("httpOnly", False),
            secure=payload.get("secure", False),
            same_site=payload.get("sameSite"),
        )


RouteHandler = Callable[[Any], Awaitable[None]]


@dataclass(slots=True)
class RouteRule:
    pattern: str
    handler: RouteHandler


class StealthHook(Protocol):
    async def __call__(self, context: Any) -> None: ...


class CaptchaHook(Protocol):
    async def __call__(self, page: Any) -> None: ...
