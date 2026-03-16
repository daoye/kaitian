import pytest

from browser import BrowserContextOptions, BrowserManager


class FakeContext:
    def __init__(self) -> None:
        self.cookies_payload = []
        self.routes = []
        self.headers = {}
        self.closed = False
        self.default_timeout = None
        self.navigation_timeout = None

    def set_default_timeout(self, value):
        self.default_timeout = value

    def set_default_navigation_timeout(self, value):
        self.navigation_timeout = value

    async def route(self, pattern, handler):
        self.routes.append((pattern, handler))

    async def new_page(self):
        return object()

    async def add_cookies(self, cookies):
        self.cookies_payload.extend(cookies)

    async def cookies(self):
        return list(self.cookies_payload)

    async def storage_state(self, path=None):
        payload = {"cookies": list(self.cookies_payload), "origins": []}
        return payload

    async def set_extra_http_headers(self, headers):
        self.headers = dict(headers)

    async def close(self):
        self.closed = True


class FakeBrowser:
    def __init__(self) -> None:
        self.contexts = []
        self.closed = False

    async def new_context(self, **kwargs):
        context = FakeContext()
        self.contexts.append((context, kwargs))
        return context

    async def close(self):
        self.closed = True


class FakeEngine:
    def __init__(self, browser):
        self.browser = browser
        self.launch_calls = []

    async def launch(self, **kwargs):
        self.launch_calls.append(kwargs)
        return self.browser


class FakePlaywright:
    def __init__(self, browser):
        self.chromium = FakeEngine(browser)
        self.stopped = False

    async def stop(self):
        self.stopped = True


class FakeRunner:
    def __init__(self, playwright):
        self.playwright = playwright

    async def start(self):
        return self.playwright


def make_factory(browser, holder):
    def factory():
        playwright = FakePlaywright(browser)
        holder.append(playwright)
        return FakeRunner(playwright)

    return factory


@pytest.mark.asyncio
async def test_manager_start_and_close() -> None:
    browser = FakeBrowser()
    holder = []
    manager = BrowserManager(playwright_factory=make_factory(browser, holder))
    await manager.start()
    assert browser.closed is False
    await manager.close()
    assert browser.closed is True
    assert holder[0].stopped is True


@pytest.mark.asyncio
async def test_context_reuse() -> None:
    browser = FakeBrowser()
    manager = BrowserManager(playwright_factory=make_factory(browser, []))
    first = await manager.new_context(BrowserContextOptions(reuse_key="shared"))
    second = await manager.new_context(BrowserContextOptions(reuse_key="shared"))
    assert first is second
    await manager.close()


@pytest.mark.asyncio
async def test_cookie_helpers() -> None:
    browser = FakeBrowser()
    manager = BrowserManager(playwright_factory=make_factory(browser, []))
    await manager.set_cookies([{"name": "sid", "value": "1", "domain": ".example.com"}])
    cookies = await manager.get_cookies()
    assert cookies[0]["name"] == "sid"
    await manager.close()
