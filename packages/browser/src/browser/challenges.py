from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .scripts import load_script


@dataclass(slots=True)
class BrowserChallenge:
    provider: str
    challenge_type: str
    message: str
    site_key: str | None = None
    response_field: str | None = None
    widget_selector: str | None = None
    action: str | None = None


_DETECT_BROWSER_CHALLENGE_SCRIPT = load_script("detect_browser_challenge")
_APPLY_BROWSER_CHALLENGE_TOKEN_SCRIPT = load_script("apply_browser_challenge_token")


def _is_transient_navigation_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return (
        "execution context was destroyed" in message
        or "most likely because of a navigation" in message
        or "cannot find context with specified id" in message
    )


async def detect_browser_challenge(page: Any) -> BrowserChallenge | None:
    try:
        title = ((await page.title()) or "").strip().lower()
        body_text = ((await page.locator("body").inner_text()) or "").strip().lower()
    except Exception as exc:
        if _is_transient_navigation_error(exc):
            return None
        raise

    if any(token in title for token in ("just a moment", "请稍候")) or any(
        token in body_text
        for token in (
            "security verification",
            "执行安全验证",
            "cloudflare",
            "verify you are not a bot",
            "验证您不是自动程序",
        )
    ):
        return BrowserChallenge(
            provider="cloudflare",
            challenge_type="interstitial",
            message="Cloudflare verification page detected",
        )

    try:
        challenge_data = await page.evaluate(_DETECT_BROWSER_CHALLENGE_SCRIPT)
    except Exception as exc:
        if _is_transient_navigation_error(exc):
            return None
        raise

    if not challenge_data:
        return None

    return BrowserChallenge(
        provider=challenge_data["provider"],
        challenge_type=challenge_data["challenge_type"],
        message=challenge_data["message"],
        site_key=challenge_data.get("site_key"),
        response_field=challenge_data.get("response_field"),
        widget_selector=challenge_data.get("widget_selector"),
        action=challenge_data.get("action"),
    )


async def apply_browser_challenge_token(page: Any, challenge: BrowserChallenge, token: str) -> None:
    await page.evaluate(
        _APPLY_BROWSER_CHALLENGE_TOKEN_SCRIPT,
        {"token": token, "responseField": challenge.response_field},
    )
