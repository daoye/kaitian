from browser.types import BrowserContextOptions, BrowserLaunchOptions, Cookie


def test_cookie_round_trip() -> None:
    cookie = Cookie(name="sid", value="abc", domain=".example.com", secure=True)
    payload = cookie.to_playwright()
    recreated = Cookie.from_playwright(payload)
    assert recreated.name == "sid"
    assert recreated.domain == ".example.com"
    assert recreated.secure is True


def test_launch_defaults() -> None:
    options = BrowserLaunchOptions()
    assert options.engine == "chromium"
    assert options.headless is True


def test_context_options_defaults() -> None:
    options = BrowserContextOptions()
    assert options.extra_http_headers == {}
    assert options.reuse_key is None
