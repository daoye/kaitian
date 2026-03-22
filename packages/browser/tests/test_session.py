import pytest

from browser import BrowserManager
from core.models import Session


class FakeContext:
    def __init__(self) -> None:
        self.cookies_payload = []
        self.headers = {}

    async def new_page(self):
        return object()

    async def add_cookies(self, cookies):
        self.cookies_payload.extend(cookies)

    async def cookies(self):
        return list(self.cookies_payload)

    async def storage_state(self, path=None):
        return {"cookies": list(self.cookies_payload), "origins": []}

    async def set_extra_http_headers(self, headers):
        self.headers = dict(headers)

    async def close(self):
        return None

    def set_default_timeout(self, value):
        return None

    def set_default_navigation_timeout(self, value):
        return None

    async def route(self, pattern, handler):
        return None


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

    async def launch(self, **kwargs):
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
async def test_apply_session_sets_cookies_and_headers() -> None:
    browser = FakeBrowser()
    manager = BrowserManager(playwright_factory=make_factory(browser, []))
    session = Session(
        session_id="s1",
        site="znzmo.com",
        account_id="demo",
        cookies={"sid": "cookie-value"},
        headers={"User-Agent": "UA"},
    )
    await manager.apply_session(session)
    cookies = await manager.get_cookies()
    assert cookies[0]["domain"] == ".znzmo.com"
    context = await manager.get_default_context()
    assert context.raw.headers["User-Agent"] == "UA"
    await manager.close()
