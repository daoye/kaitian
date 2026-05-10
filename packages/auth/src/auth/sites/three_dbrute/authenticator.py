from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from browser import (
    BrowserContextOptions,
    BrowserLaunchOptions,
    BrowserChallenge,
    BrowserManager,
    apply_browser_challenge_token,
    detect_browser_challenge,
)
from captcha import CaptchaChallenge, CaptchaOrchestrator, CaptchaOutcome, ManualCaptchaSolver
from core.models import Authenticator, Session
from core.wait import PollTimeoutError, poll_until
from stealth import (
    PRESET_PROFILES,
    StealthConfig,
    StealthManager,
)

from auth.exceptions import (
    CaptchaRequiredError,
    InvalidCredentialsError,
    LoginFailedError,
    SessionExpiredError,
)


class ThreeDBruteAuthenticator(Authenticator):
    BASE_URL = "https://3dbrute.com"
    HOME_URL = "https://3dbrute.com/"
    LOGIN_URL = "https://3dbrute.com/login/"
    DASHBOARD_URL = "https://3dbrute.com/dashboard-2/?udb_page=purchases"
    LOGOUT_URL = "https://3dbrute.com/logout"

    DEFAULT_SELECTORS = {
        "login_form": "#custom-login-form",
        "username_input": "input[name='username']",
        "password_input": "input[name='password']",
        "login_button": "#login-submit",
        "error_message": "article p",
        "logout_link": "a[href='https://3dbrute.com/logout'], a[href='/logout']",
        "dashboard_marker": "text=Overview & Purchases",
    }

    def __init__(
        self,
        timeout: int = 3000000,
        selectors: Optional[Dict[str, str]] = None,
        captcha_solver: Any | None = None,
    ) -> None:
        self._timeout = timeout
        self._selectors = {**self.DEFAULT_SELECTORS, **(selectors or {})}
        self._captcha_orchestrator = CaptchaOrchestrator(
            [captcha_solver] if captcha_solver is not None else [ManualCaptchaSolver()]
        )
        self._challenge_history: list[dict[str, str]] = []
        self._post_challenge_settle_urls: list[dict[str, str]] = []
        self._stealth_profile = PRESET_PROFILES["chrome_windows"]
        self._stealth_manager = StealthManager(
            StealthConfig(
                enabled=True,
                fingerprint_preset="chrome_windows",
            ),
            custom_profile=self._stealth_profile,
        )

    def _create_context_options(self) -> BrowserContextOptions:
        context_options = self._stealth_profile.to_context_options()
        return BrowserContextOptions(
            base_url=self.BASE_URL,
            user_agent=context_options["user_agent"],
            viewport=context_options["viewport"],
            locale=context_options["locale"],
            timezone_id=context_options["timezone_id"],
            extra_http_headers=context_options["extra_http_headers"],
        )

    def _get_selector(self, key: str) -> str:
        return self._selectors[key]

    def _reset_runtime_observability(self) -> None:
        """重置运行时可观测性状态."""
        self._challenge_history.clear()
        self._post_challenge_settle_urls.clear()

    def _record_challenge(self, page: Any, challenge: BrowserChallenge | None) -> None:
        """记录 challenge 到历史记录中."""
        if challenge is None:
            return

        entry = {
            "type": challenge.challenge_type,
            "provider": challenge.provider,
            "url": page.url,
            "timestamp": datetime.now().isoformat(),
        }

        # 去重：只有当 (type, provider, url) 与上一次不同时才记录
        if self._challenge_history:
            last_entry = self._challenge_history[-1]
            if (
                last_entry["type"] == entry["type"]
                and last_entry["provider"] == entry["provider"]
                and last_entry["url"] == entry["url"]
            ):
                return

        self._challenge_history.append(entry)

    def _record_settle_url(self, page: Any) -> None:
        """记录挑战后页面稳定的 URL."""
        entry = {
            "url": page.url,
            "timestamp": datetime.now().isoformat(),
        }
        self._post_challenge_settle_urls.append(entry)

    async def _detect_challenge(self, page: Any) -> BrowserChallenge | None:
        """包装 detect_browser_challenge 以记录 challenge 类型迁移."""
        challenge = await detect_browser_challenge(page)
        self._record_challenge(page, challenge)
        return challenge

    def _build_session_metadata(self, user_agent: str | None) -> dict[str, Any]:
        """构建会话元数据，包括运行时可观测性信息."""
        return {
            "cookie_domain": ".3dbrute.com",
            "login_time": datetime.now().isoformat(),
            "login_url": self.LOGIN_URL,
            "user_agent": user_agent,
            "challenge_history": list(self._challenge_history),
            "post_challenge_settle_urls": list(self._post_challenge_settle_urls),
        }

    async def _close_page_safely(self, page: Any) -> None:
        if page is None:
            return
        try:
            await page.close()
        except Exception:
            return

    async def _close_context_safely(self, context: Any) -> None:
        if context is None:
            return
        try:
            await context.close()
        except Exception:
            return

    async def _new_context(self, browser_manager: Any) -> Any:
        return await browser_manager.new_context(self._create_context_options())

    async def _open_page(self, context: Any, url: str) -> Any:
        page = await context.new_page()
        await page.goto(url, wait_until="load")
        return page

    async def _apply_session_cookies(self, context: Any, session: Session) -> None:
        await context.add_cookies(
            [
                {
                    "name": name,
                    "value": value,
                    "domain": session.metadata.get("cookie_domain", ".3dbrute.com"),
                    "path": "/",
                }
                for name, value in session.cookies.items()
            ]
        )

    async def _read_auth_markers(self, page: Any) -> tuple[str, int, int]:
        current_url = page.url
        logout_count = await page.locator(self._get_selector("logout_link")).count()
        dashboard_count = await page.locator(self._get_selector("dashboard_marker")).count()
        return current_url, logout_count, dashboard_count

    async def _is_login_form_visible(self, page: Any) -> bool:
        locator = page.locator(self._get_selector("login_form"))
        if await locator.count() == 0:
            return False
        return await locator.first.is_visible()

    async def _sleep_for(self, action: str) -> None:
        await asyncio.sleep(self._stealth_manager.get_random_delay(action))

    async def _move_to(self, page: Any, selector: str) -> None:
        locator = page.locator(selector).first
        box = await locator.bounding_box()
        if not box:
            return
        await page.mouse.move(
            box["x"] + box["width"] / 2,
            box["y"] + box["height"] / 2,
            steps=20,
        )

    async def _human_type(self, page: Any, selector: str, value: str) -> None:
        locator = page.locator(selector).first
        await self._move_to(page, selector)
        await self._sleep_for("click")
        await locator.click()
        await self._sleep_for("wait")
        await locator.fill("")
        for char in value:
            await locator.type(char)
            await self._sleep_for("type")

    async def _human_click(self, page: Any, selector: str) -> None:
        await self._move_to(page, selector)
        await self._sleep_for("click")
        await page.locator(selector).first.click()

    async def _raise_if_security_challenge(self, page: Any) -> None:
        challenge = await self._detect_challenge(page)
        if challenge is None:
            return
        if challenge.provider == "cloudflare" and challenge.challenge_type == "interstitial":
            await self._wait_for_manual_challenge(page, challenge.message)

    async def _is_page_closed(self, page: Any) -> bool:
        is_closed = getattr(page, "is_closed", None)
        if callable(is_closed):
            try:
                return bool(is_closed())
            except Exception:
                return False
        return False

    async def _wait_for_manual_challenge(self, page: Any, message: str) -> None:
        if self._headless:
            raise CaptchaRequiredError(message)

        while True:
            if await self._is_page_closed(page):
                raise CaptchaRequiredError(message)

            challenge = await self._detect_challenge(page)
            if challenge is None:
                settled = await self._wait_for_post_challenge_settle(page)
                if settled:
                    return

            await asyncio.sleep(0.5)

    async def _wait_for_post_challenge_settle(self, page: Any) -> bool:
        stable_rounds = 0
        previous_url = page.url

        # 记录初始 URL
        self._record_settle_url(page)

        while stable_rounds < 3:
            if await self._is_page_closed(page):
                return False

            challenge = await self._detect_challenge(page)
            if challenge is not None:
                return False

            try:
                await page.wait_for_load_state("load", timeout=1000)
            except Exception:
                pass

            await asyncio.sleep(0.5)

            current_url = page.url
            challenge = await self._detect_challenge(page)
            if challenge is not None:
                return False

            # URL 发生变化时记录
            if current_url != previous_url:
                self._record_settle_url(page)

            if current_url == previous_url:
                stable_rounds += 1
            else:
                stable_rounds = 0
                previous_url = current_url

        return True

    async def _warm_up(self, page: Any) -> None:
        await page.goto(self.HOME_URL, wait_until="load")
        await self._raise_if_security_challenge(page)
        await self._sleep_for("wait")
        await page.mouse.move(240, 180, steps=16)
        await self._sleep_for("scroll")
        await page.mouse.wheel(0, 360)
        await self._sleep_for("scroll")
        await page.mouse.wheel(0, -220)
        await self._sleep_for("wait")
        await self._raise_if_security_challenge(page)

        token_applied = await self._solve_token_challenge(page)
        if token_applied:
            await self._sleep_for("wait")

    async def _build_captcha_challenge(
        self, page: Any, challenge: BrowserChallenge
    ) -> CaptchaChallenge:
        return CaptchaChallenge(
            site="3dbrute",
            challenge_type=challenge.challenge_type,
            page_url=page.url,
            metadata={"message": challenge.message},
            provider=challenge.provider,
            site_key=challenge.site_key,
            response_field=challenge.response_field,
            widget_selector=challenge.widget_selector,
            action=challenge.action,
            invisible=True,
        )

    async def _solve_token_challenge(self, page: Any) -> bool:
        challenge = await self._detect_challenge(page)
        if challenge is None or challenge.challenge_type not in {"turnstile", "recaptcha"}:
            return False
        captcha_challenge = await self._build_captcha_challenge(page, challenge)
        outcome = await self._captcha_orchestrator.solve(captcha_challenge)
        if outcome.status != CaptchaOutcome.STATUS_SOLVED or not outcome.token:
            await self._wait_for_manual_challenge(page, challenge.message)
            return True
        await apply_browser_challenge_token(page, challenge, outcome.token)
        return True

    async def _wait_for_login_form_ready(self, page: Any) -> None:
        async def check_form() -> bool | None:
            challenge = await self._detect_challenge(page)
            if challenge is not None:
                await self._raise_if_security_challenge(page)
            if await self._is_login_form_visible(page):
                return True
            return None

        try:
            await poll_until(
                check_form,
                timeout=self._timeout / 1000,
                interval=0.2,
            )
        except PollTimeoutError as exc:
            await self._raise_if_security_challenge(page)
            raise LoginFailedError(
                "3dbrute login form not available", reason="form_not_found"
            ) from exc

    async def _read_login_error(self, page: Any) -> str | None:
        locator = page.locator(self._get_selector("error_message"))
        count = await locator.count()
        for index in range(count):
            text = await locator.nth(index).text_content()
            if text is None:
                continue
            normalized = text.strip()
            lowered = normalized.lower()
            if not normalized:
                continue
            if "privacy policy" in lowered or "don’t have an account yet" in lowered:
                continue
            if "protected by recaptcha" in lowered:
                continue
            if any(
                token in lowered
                for token in ("does not exist", "incorrect", "invalid", "password", "email")
            ):
                return normalized
            if any(token in lowered for token in ("captcha", "recaptcha", "robot")):
                await self._wait_for_manual_challenge(page, normalized)
                return None
        return None

    async def _has_auth_cookies(self, context: Any) -> bool:
        cookies = await context.cookies()
        for cookie in cookies:
            name = cookie.get("name", "")
            if name.startswith("wordpress_logged_in") or name.startswith("wordpress_sec"):
                return True
        return False

    async def _extract_cookie_dict(self, context: Any) -> dict[str, str]:
        cookies = await context.cookies()
        return {
            cookie["name"]: cookie["value"]
            for cookie in cookies
            if cookie.get("name") and cookie.get("value")
        }

    async def _wait_for_login_outcome(self, page: Any, context: Any) -> None:
        async def check_outcome() -> bool | None:
            await self._raise_if_security_challenge(page)
            error_message = await self._read_login_error(page)
            if error_message is not None:
                raise InvalidCredentialsError(error_message)

            login_form_visible = await self._is_login_form_visible(page)
            has_auth_cookies = await self._has_auth_cookies(context)
            current_url, logout_count, dashboard_count = await self._read_auth_markers(page)

            if has_auth_cookies and (
                "/login" not in current_url
                or (not login_form_visible and logout_count > 0)
                or (logout_count > 0 and dashboard_count > 0)
            ):
                return True
            return None

        try:
            await poll_until(
                check_outcome,
                timeout=self._timeout / 1000,
                interval=0.2,
            )
        except PollTimeoutError as exc:
            raise LoginFailedError(
                "3dbrute login did not complete", reason="login_timeout"
            ) from exc

    async def login(
        self,
        credentials: Dict[str, Any],
        browser_manager: Any,
    ) -> Session:
        username = str(credentials.get("username") or "").strip()
        password = str(credentials.get("password") or "").strip()
        if not username or not password:
            raise InvalidCredentialsError("username and password are required")

        context = None
        page = None

        try:
            # 重置运行时可观测性状态
            self._reset_runtime_observability()

            context = await self._new_context()
            page = await context.new_page()
            await self._warm_up(page)
            await page.goto(self.LOGIN_URL, wait_until="load")
            await self._sleep_for("wait")
            await self._wait_for_login_form_ready(page)

            await self._human_type(page, self._get_selector("username_input"), username)
            await self._sleep_for("wait")
            await self._human_type(page, self._get_selector("password_input"), password)
            await self._sleep_for("wait")
            token_applied = await self._solve_token_challenge(page)
            if token_applied:
                await self._sleep_for("wait")
            await self._human_click(page, self._get_selector("login_button"))

            await self._wait_for_login_outcome(page, context)

            cookies = await self._extract_cookie_dict(context)
            if not cookies:
                raise LoginFailedError(
                    "3dbrute login did not produce cookies", reason="missing_cookies"
                )

            user_agent = await page.evaluate("() => navigator.userAgent")
            return Session(
                session_id=str(uuid.uuid4()),
                site="3dbrute",
                account_id=username,
                cookies=cookies,
                headers={"User-Agent": user_agent} if isinstance(user_agent, str) else {},
                expires_at=datetime.now() + timedelta(days=7),
                metadata=self._build_session_metadata(user_agent),
            )
        finally:
            await self._close_page_safely(page)
            await self._close_context_safely(context)

    async def verify(
        self,
        session: Session,
        browser_manager: Any,
    ) -> bool:
        if session.is_expired() or not session.cookies:
            return False

        context = None
        page = None

        try:
            context = await self._new_context(browser_manager)
            await self._apply_session_cookies(context, session)
            page = await self._open_page(context, self.DASHBOARD_URL)
            has_auth_cookies = await self._has_auth_cookies(context)
            current_url, logout_count, dashboard_count = await self._read_auth_markers(page)
            if has_auth_cookies and (
                "/login" not in current_url or (logout_count > 0 and dashboard_count > 0)
            ):
                return True
            return False
        except Exception as exc:
            raise LoginFailedError(
                "Failed to verify 3dbrute session",
                reason="verify_failed",
                details={"error": str(exc)},
            ) from exc
        finally:
            await self._close_page_safely(page)
            await self._close_context_safely(context)

    async def refresh(
        self,
        session: Session,
        browser_manager: Any,
    ) -> Session:
        if session.is_expired():
            raise SessionExpiredError("Session has already expired")
        is_valid = await self.verify(session, browser_manager)
        if not is_valid:
            raise SessionExpiredError("Session is no longer valid")
        session.expires_at = datetime.now() + timedelta(days=7)
        session.update_usage()
        return session

    async def logout(
        self,
        session: Session,
        browser_manager: Any,
    ) -> bool:
        context = None
        page = None

        try:
            context = await self._new_context(browser_manager)
            await self._apply_session_cookies(context, session)
            page = await self._open_page(context, self.LOGOUT_URL)
            return True
        except Exception as exc:
            raise LoginFailedError(
                "Failed to logout from 3dbrute",
                reason="logout_failed",
                details={"error": str(exc)},
            ) from exc
        finally:
            await self._close_page_safely(page)
            await self._close_context_safely(context)
