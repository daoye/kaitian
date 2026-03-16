import pytest

from browser import BrowserManager
from core.models import Session

from .test_manager import FakeBrowser, make_factory


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
