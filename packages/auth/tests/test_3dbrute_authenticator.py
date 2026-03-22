from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from auth.exceptions import CaptchaRequiredError, InvalidCredentialsError
from auth.sites.three_dbrute.authenticator import ThreeDBruteAuthenticator
from core.models import Session


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

        with pytest.raises(CaptchaRequiredError):
            await authenticator.login({"username": "test@example.com", "password": "secret"})


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
