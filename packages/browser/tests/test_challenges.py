from unittest.mock import AsyncMock, MagicMock

import pytest

from browser.challenges import apply_browser_challenge_token, detect_browser_challenge


@pytest.mark.asyncio
async def test_detect_cloudflare_interstitial():
    page = AsyncMock()
    page.title = AsyncMock(return_value="Just a moment...")
    body_locator = MagicMock()
    body_locator.inner_text = AsyncMock(return_value="Performing security verification")
    page.locator = MagicMock(return_value=body_locator)

    challenge = await detect_browser_challenge(page)

    assert challenge is not None
    assert challenge.provider == "cloudflare"
    assert challenge.challenge_type == "interstitial"


@pytest.mark.asyncio
async def test_detect_recaptcha_widget():
    page = AsyncMock()
    page.title = AsyncMock(return_value="Login")
    body_locator = MagicMock()
    body_locator.inner_text = AsyncMock(return_value="Login page")

    def locator_side_effect(selector):
        if selector == "body":
            return body_locator
        return MagicMock()

    page.locator = MagicMock(side_effect=locator_side_effect)
    page.evaluate = AsyncMock(
        return_value={
            "provider": "google",
            "challenge_type": "recaptcha",
            "message": "Google reCAPTCHA detected",
            "site_key": "site-key-123",
            "response_field": "g-recaptcha-response",
            "widget_selector": ".g-recaptcha",
            "action": "login",
        }
    )

    challenge = await detect_browser_challenge(page)

    assert challenge is not None
    assert challenge.provider == "google"
    assert challenge.site_key == "site-key-123"
    assert challenge.response_field == "g-recaptcha-response"


@pytest.mark.asyncio
async def test_apply_browser_challenge_token_uses_extracted_script():
    page = AsyncMock()
    challenge = MagicMock(response_field="g-recaptcha-response")

    await apply_browser_challenge_token(page, challenge, "token-123")

    page.evaluate.assert_awaited_once()
    script, payload = page.evaluate.await_args.args
    assert "g-recaptcha-response" in script
    assert "data-callback" in script
    assert "___grecaptcha_cfg" in script
    assert payload == {"token": "token-123", "responseField": "g-recaptcha-response"}


@pytest.mark.asyncio
async def test_detect_browser_challenge_ignores_transient_navigation_error():
    page = AsyncMock()
    page.title = AsyncMock(
        side_effect=Exception(
            "Page.title: Execution context was destroyed, most likely because of a navigation"
        )
    )

    challenge = await detect_browser_challenge(page)

    assert challenge is None
