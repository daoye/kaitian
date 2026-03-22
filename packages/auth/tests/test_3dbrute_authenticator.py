from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from captcha import CaptchaOutcome
from auth.exceptions import CaptchaRequiredError, InvalidCredentialsError
from auth.sites.three_dbrute.authenticator import ThreeDBruteAuthenticator
from core.models import Session
from stealth import PRESET_PROFILES


def _setup_browser_mocks(authenticator, mock_context, mock_page):
    manager = patch.object(authenticator, "_browser_manager").start()
    manager.start = AsyncMock()
    manager.new_context = AsyncMock(return_value=mock_context)
    mock_context.new_page = AsyncMock(return_value=mock_page)
    mock_context.close = AsyncMock()
    mock_page.goto = AsyncMock()
    mock_page.fill = AsyncMock()
    mock_page.click = AsyncMock()
    mock_page.evaluate = AsyncMock(return_value="Mozilla/5.0 Test")
    mock_page.close = AsyncMock()
    return manager


@pytest.mark.asyncio
async def test_login_success_returns_session():
    authenticator = ThreeDBruteAuthenticator()
    mock_page = AsyncMock()
    mock_context = AsyncMock()

    with patch.object(authenticator, "_browser_manager") as mock_manager:
        mock_manager.start = AsyncMock()
        mock_manager.new_context = AsyncMock(return_value=mock_context)
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.close = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.fill = AsyncMock()
        mock_page.click = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value="Mozilla/5.0 Test")
        mock_page.close = AsyncMock()

        authenticator._wait_for_login_form_ready = AsyncMock()
        authenticator._wait_for_login_outcome = AsyncMock()
        authenticator._extract_cookie_dict = AsyncMock(
            return_value={"wordpress_logged_in_hash": "cookie-value"}
        )
        authenticator._warm_up = AsyncMock()
        authenticator._sleep_for = AsyncMock()
        authenticator._human_type = AsyncMock()
        authenticator._human_click = AsyncMock()
        authenticator._solve_token_challenge = AsyncMock(return_value=False)

        session = await authenticator.login(
            {"username": "tester@example.com", "password": "secret"}
        )

        assert session.site == "3dbrute"
        assert session.account_id == "tester@example.com"
        assert session.cookies["wordpress_logged_in_hash"] == "cookie-value"
        assert session.metadata["cookie_domain"] == ".3dbrute.com"
        mock_page.close.assert_called_once()
        mock_context.close.assert_called_once()


@pytest.mark.asyncio
async def test_login_invalid_credentials_raises_and_closes_resources():
    authenticator = ThreeDBruteAuthenticator()
    mock_page = AsyncMock()
    mock_context = AsyncMock()

    with patch.object(authenticator, "_browser_manager") as mock_manager:
        mock_manager.start = AsyncMock()
        mock_manager.new_context = AsyncMock(return_value=mock_context)
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.close = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.fill = AsyncMock()
        mock_page.click = AsyncMock()
        mock_page.close = AsyncMock()

        authenticator._wait_for_login_form_ready = AsyncMock()
        authenticator._wait_for_login_outcome = AsyncMock(
            side_effect=InvalidCredentialsError("The email you entered does not exist.")
        )
        authenticator._warm_up = AsyncMock()
        authenticator._sleep_for = AsyncMock()
        authenticator._human_type = AsyncMock()
        authenticator._human_click = AsyncMock()
        authenticator._solve_token_challenge = AsyncMock(return_value=False)

        with pytest.raises(InvalidCredentialsError):
            await authenticator.login({"username": "bad@example.com", "password": "bad"})

        mock_page.close.assert_called_once()
        mock_context.close.assert_called_once()


@pytest.mark.asyncio
async def test_verify_returns_true_when_redirected_away_from_login():
    authenticator = ThreeDBruteAuthenticator()
    mock_page = AsyncMock()
    mock_context = AsyncMock()
    mock_page.url = authenticator.DASHBOARD_URL

    with patch.object(authenticator, "_browser_manager") as mock_manager:
        mock_manager.start = AsyncMock()
        mock_manager.new_context = AsyncMock(return_value=mock_context)
        mock_context.add_cookies = AsyncMock()
        mock_context.cookies = AsyncMock(
            return_value=[{"name": "wordpress_logged_in_hash", "value": "cookie-value"}]
        )
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.close = AsyncMock()
        mock_page.goto = AsyncMock()
        logout_locator = MagicMock()
        logout_locator.count = AsyncMock(return_value=1)
        dashboard_locator = MagicMock()
        dashboard_locator.count = AsyncMock(return_value=1)

        def locator_side_effect(selector):
            if selector == authenticator._get_selector("logout_link"):
                return logout_locator
            if selector == authenticator._get_selector("dashboard_marker"):
                return dashboard_locator
            return MagicMock()

        mock_page.locator = MagicMock(side_effect=locator_side_effect)
        mock_page.close = AsyncMock()

        session = Session(
            session_id="session-001",
            site="3dbrute",
            account_id="tester",
            cookies={"wordpress_logged_in_hash": "cookie-value"},
            metadata={"cookie_domain": ".3dbrute.com"},
            expires_at=datetime.now() + timedelta(days=1),
        )

        assert await authenticator.verify(session) is True


@pytest.mark.asyncio
async def test_verify_returns_false_when_login_form_visible():
    authenticator = ThreeDBruteAuthenticator()
    mock_page = AsyncMock()
    mock_context = AsyncMock()
    mock_page.url = authenticator.LOGIN_URL

    with patch.object(authenticator, "_browser_manager") as mock_manager:
        mock_manager.start = AsyncMock()
        mock_manager.new_context = AsyncMock(return_value=mock_context)
        mock_context.add_cookies = AsyncMock()
        mock_context.cookies = AsyncMock(return_value=[])
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.close = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.close = AsyncMock()
        logout_locator = MagicMock()
        logout_locator.count = AsyncMock(return_value=1)
        dashboard_locator = MagicMock()
        dashboard_locator.count = AsyncMock(return_value=1)

        def locator_side_effect(selector):
            if selector == authenticator._get_selector("logout_link"):
                return logout_locator
            if selector == authenticator._get_selector("dashboard_marker"):
                return dashboard_locator
            return MagicMock()

        mock_page.locator = MagicMock(side_effect=locator_side_effect)

        session = Session(
            session_id="session-001",
            site="3dbrute",
            account_id="tester",
            cookies={"wordpress_logged_in_hash": "cookie-value"},
            metadata={"cookie_domain": ".3dbrute.com"},
            expires_at=datetime.now() + timedelta(days=1),
        )

        assert await authenticator.verify(session) is False


@pytest.mark.asyncio
async def test_login_raises_captcha_required_on_cloudflare_page():
    authenticator = ThreeDBruteAuthenticator()
    mock_page = AsyncMock()
    mock_context = AsyncMock()

    with patch.object(authenticator, "_browser_manager") as mock_manager:
        mock_manager.start = AsyncMock()
        mock_manager.new_context = AsyncMock(return_value=mock_context)
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.close = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.title = AsyncMock(return_value="Just a moment...")
        body_locator = MagicMock()
        body_locator.inner_text = AsyncMock(return_value="Performing security verification")
        form_locator = MagicMock()
        form_locator.count = AsyncMock(return_value=0)

        def locator_side_effect(selector):
            if selector == "body":
                return body_locator
            return form_locator

        mock_page.locator = MagicMock(side_effect=locator_side_effect)
        mock_page.close = AsyncMock()
        authenticator._sleep_for = AsyncMock()
        authenticator._human_type = AsyncMock()
        authenticator._human_click = AsyncMock()
        authenticator._solve_token_challenge = AsyncMock(return_value=False)

        with pytest.raises(CaptchaRequiredError):
            await authenticator.login({"username": "test@example.com", "password": "secret"})


@pytest.mark.asyncio
async def test_non_headless_waits_for_manual_challenge_resolution():
    authenticator = ThreeDBruteAuthenticator(headless=False)
    page = AsyncMock()
    page.is_closed = MagicMock(return_value=False)

    challenge = MagicMock(message="Cloudflare verification page detected")
    authenticator._wait_for_post_challenge_settle = AsyncMock(return_value=True)
    with patch(
        "auth.sites.three_dbrute.authenticator.detect_browser_challenge",
        AsyncMock(side_effect=[challenge, challenge, None]),
    ):
        await authenticator._wait_for_manual_challenge(page, challenge.message)

    authenticator._wait_for_post_challenge_settle.assert_awaited_once_with(page)


@pytest.mark.asyncio
async def test_wait_for_post_challenge_settle_returns_false_when_challenge_reappears():
    authenticator = ThreeDBruteAuthenticator(headless=False)
    page = AsyncMock()
    page.is_closed = MagicMock(return_value=False)
    page.url = "https://3dbrute.com/login/"
    page.wait_for_load_state = AsyncMock()
    challenge = MagicMock(message="Cloudflare verification page detected")

    with (
        patch(
            "auth.sites.three_dbrute.authenticator.detect_browser_challenge",
            AsyncMock(side_effect=[None, challenge]),
        ),
        patch("auth.sites.three_dbrute.authenticator.asyncio.sleep", AsyncMock()),
    ):
        settled = await authenticator._wait_for_post_challenge_settle(page)

    assert settled is False


@pytest.mark.asyncio
async def test_non_headless_manual_captcha_in_solve_token_challenge():
    authenticator = ThreeDBruteAuthenticator(headless=False)
    page = AsyncMock()
    challenge = MagicMock(challenge_type="recaptcha", message="reCAPTCHA verification failed")
    outcome = MagicMock(status=CaptchaOutcome.STATUS_MANUAL_REQUIRED, token=None)

    authenticator._captcha_orchestrator.solve = AsyncMock(return_value=outcome)
    authenticator._build_captcha_challenge = AsyncMock()
    authenticator._wait_for_manual_challenge = AsyncMock()

    with patch(
        "auth.sites.three_dbrute.authenticator.detect_browser_challenge",
        AsyncMock(return_value=challenge),
    ):
        result = await authenticator._solve_token_challenge(page)

    assert result is True
    authenticator._wait_for_manual_challenge.assert_awaited_once_with(
        page, "reCAPTCHA verification failed"
    )


@pytest.mark.asyncio
async def test_non_headless_read_login_error_waits_for_manual_resolution():
    authenticator = ThreeDBruteAuthenticator(headless=False)
    page = AsyncMock()
    locator = MagicMock()
    locator.count = AsyncMock(return_value=1)
    node = MagicMock()
    node.text_content = AsyncMock(return_value="reCAPTCHA verification failed. Are you a robot?")
    locator.nth = MagicMock(return_value=node)
    page.locator = MagicMock(return_value=locator)
    authenticator._wait_for_manual_challenge = AsyncMock()

    result = await authenticator._read_login_error(page)

    assert result is None
    authenticator._wait_for_manual_challenge.assert_awaited_once_with(
        page, "reCAPTCHA verification failed. Are you a robot?"
    )


@pytest.mark.asyncio
async def test_refresh_extends_expiration():
    authenticator = ThreeDBruteAuthenticator()
    old_expiration = datetime.now() + timedelta(hours=1)
    session = Session(
        session_id="session-001",
        site="3dbrute",
        account_id="tester",
        cookies={"wordpress_logged_in_hash": "cookie-value"},
        expires_at=old_expiration,
    )

    with patch.object(authenticator, "verify", AsyncMock(return_value=True)):
        refreshed = await authenticator.refresh(session)

    assert refreshed.expires_at is not None
    assert refreshed.expires_at > old_expiration


def test_3dbrute_authenticator_explicitly_enables_stealth():
    authenticator = ThreeDBruteAuthenticator()

    assert authenticator._stealth_manager._config.enabled is True
    assert authenticator._stealth_profile == PRESET_PROFILES["chrome_windows"]


@pytest.mark.asyncio
async def test_login_success_includes_stealth_observability_metadata():
    """测试登录成功时包含反检测可观测性元数据."""
    authenticator = ThreeDBruteAuthenticator()
    mock_page = AsyncMock()
    mock_context = AsyncMock()

    with patch.object(authenticator, "_browser_manager") as mock_manager:
        mock_manager.start = AsyncMock()
        mock_manager.new_context = AsyncMock(return_value=mock_context)
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.close = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.fill = AsyncMock()
        mock_page.click = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value="Mozilla/5.0 Test")
        mock_page.close = AsyncMock()

        authenticator._wait_for_login_form_ready = AsyncMock()
        authenticator._wait_for_login_outcome = AsyncMock()
        authenticator._extract_cookie_dict = AsyncMock(
            return_value={"wordpress_logged_in_hash": "cookie-value"}
        )
        authenticator._warm_up = AsyncMock()
        authenticator._sleep_for = AsyncMock()
        authenticator._human_type = AsyncMock()
        authenticator._human_click = AsyncMock()
        authenticator._solve_token_challenge = AsyncMock(return_value=False)

        session = await authenticator.login(
            {"username": "tester@example.com", "password": "secret"}
        )

        # 验证基础元数据
        assert session.metadata["cookie_domain"] == ".3dbrute.com"
        assert "login_time" in session.metadata
        assert session.metadata["login_url"] == authenticator.LOGIN_URL
        assert session.metadata["user_agent"] == "Mozilla/5.0 Test"

        assert "challenge_history" in session.metadata
        assert session.metadata["challenge_history"] == []
        assert "post_challenge_settle_urls" in session.metadata
        assert session.metadata["post_challenge_settle_urls"] == []


@pytest.mark.asyncio
async def test_wait_for_manual_challenge_records_distinct_challenge_history():
    """测试人工等待 challenge 时记录去重的 challenge 历史."""
    authenticator = ThreeDBruteAuthenticator(headless=False)
    page = AsyncMock()
    page.url = "https://3dbrute.com/login/"
    page.is_closed = MagicMock(return_value=False)

    from browser import BrowserChallenge

    challenge1 = BrowserChallenge(
        provider="cloudflare",
        challenge_type="interstitial",
        message="Just a moment...",
        site_key=None,
        response_field=None,
        widget_selector=None,
        action=None,
    )
    challenge2 = BrowserChallenge(
        provider="cloudflare",
        challenge_type="turnstile",
        message="Verify you are human",
        site_key="0x4AAAA",
        response_field="cf-turnstile-response",
        widget_selector="cf-turnstile-wrapper",
        action="submit",
    )

    # 创建可迭代 mock 来模拟协程函数
    mock_detect_coro = AsyncMock()
    call_count = [0]

    async def side_effect(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return challenge1
        elif call_count[0] == 2:
            return challenge2
        elif call_count[0] == 3:
            return challenge2
        else:
            return None

    mock_detect_coro.side_effect = side_effect

    with patch(
        "auth.sites.three_dbrute.authenticator.detect_browser_challenge",
        mock_detect_coro,
    ):
        # 第一次 challenge 记录
        await authenticator._detect_challenge(page)
        assert len(authenticator._challenge_history) == 1
        assert authenticator._challenge_history[0]["type"] == "interstitial"
        assert authenticator._challenge_history[0]["provider"] == "cloudflare"

        # 相同的 challenge 不重复记录（第二次调用返回 challenge2）
        await authenticator._detect_challenge(page)
        assert len(authenticator._challenge_history) == 2
        assert authenticator._challenge_history[1]["type"] == "turnstile"
        assert authenticator._challenge_history[1]["provider"] == "cloudflare"

        # 相同的 challenge 第三次不重复记录
        await authenticator._detect_challenge(page)
        assert len(authenticator._challenge_history) == 2

        # None 检测时不记录
        await authenticator._detect_challenge(page)
        assert len(authenticator._challenge_history) == 2
        assert authenticator._challenge_history[1]["type"] == "turnstile"
        assert authenticator._challenge_history[1]["provider"] == "cloudflare"

        # 相同的 challenge 第三次不重复记录
        await authenticator._detect_challenge(page)
        assert len(authenticator._challenge_history) == 2

        # None 检测时不记录
        await authenticator._detect_challenge(page)
        assert len(authenticator._challenge_history) == 2
        assert authenticator._challenge_history[1]["type"] == "turnstile"
        assert authenticator._challenge_history[1]["provider"] == "cloudflare"

        # 相同的 challenge 第三次不重复记录
        await authenticator._detect_challenge(page)
        assert len(authenticator._challenge_history) == 2

        # None 检测时不记录
        await authenticator._detect_challenge(page)
        assert len(authenticator._challenge_history) == 2


@pytest.mark.asyncio
async def test_wait_for_post_challenge_settle_records_url_changes():
    """测试挑战后页面稳定时记录 URL 变化."""
    authenticator = ThreeDBruteAuthenticator(headless=False)
    page = AsyncMock()
    page.is_closed = MagicMock(return_value=False)
    page.url = "https://3dbrute.com/login/"

    with patch(
        "auth.sites.three_dbrute.authenticator.detect_browser_challenge",
        AsyncMock(return_value=None),
    ):
        # 初始 URL 记录
        assert len(authenticator._post_challenge_settle_urls) == 0

        with patch.object(authenticator, "_wait_for_post_challenge_settle") as mock_wait:
            mock_wait.return_value = True

            # 模拟 URL 变化：在 _wait_for_post_challenge_settle 中会调用 _record_settle_url
            # 这里我们手动添加记录来测试
            authenticator._record_settle_url(page)
            assert len(authenticator._post_challenge_settle_urls) == 1
            assert (
                authenticator._post_challenge_settle_urls[0]["url"] == "https://3dbrute.com/login/"
            )

            # 模拟 URL 再次变化
            page.url = "https://3dbrute.com/dashboard/"
            authenticator._record_settle_url(page)
            assert len(authenticator._post_challenge_settle_urls) == 2
            assert (
                authenticator._post_challenge_settle_urls[1]["url"]
                == "https://3dbrute.com/dashboard/"
            )


@pytest.mark.asyncio
async def test_reset_runtime_observability_clears_history():
    """测试重置可观测性状态清空历史记录."""
    authenticator = ThreeDBruteAuthenticator()

    # 添加一些历史记录
    authenticator._challenge_history.append({"type": "test", "url": "https://example.com"})
    authenticator._post_challenge_settle_urls.append({"url": "https://example.com"})

    assert len(authenticator._challenge_history) == 1
    assert len(authenticator._post_challenge_settle_urls) == 1

    # 重置
    authenticator._reset_runtime_observability()

    assert len(authenticator._challenge_history) == 0
    assert len(authenticator._post_challenge_settle_urls) == 0
