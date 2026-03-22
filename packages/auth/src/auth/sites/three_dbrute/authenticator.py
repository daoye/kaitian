from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from browser import BrowserContextOptions, BrowserLaunchOptions, BrowserManager
from core.models import Authenticator, Session
from core.wait import PollTimeoutError, poll_until
from stealth import StealthConfig, StealthManager

from auth.exceptions import (
    CaptchaRequiredError,
    InvalidCredentialsError,
    LoginFailedError,
    SessionExpiredError,
)


class ThreeDBruteAuthenticator(Authenticator):
    BASE_URL = "https://3dbrute.com"
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
        timeout: int = 300000,
        selectors: Optional[Dict[str, str]] = None,
        headless: bool = True,
        proxy: Optional[Dict[str, str]] = None,
    ) -> None:
        self._timeout = timeout
        self._selectors = {**self.DEFAULT_SELECTORS, **(selectors or {})}
        self._stealth_manager = StealthManager(
            StealthConfig(fingerprint_preset="chrome_windows", noise_level="medium")
        )
        self._stealth_plan = self._stealth_manager.build_plan(self.BASE_URL)

        async def stealth_hook(context: Any) -> None:
            await self._stealth_manager.apply_to_context(context, self.BASE_URL)

        self._browser_manager = BrowserManager(
            launch_options=BrowserLaunchOptions(
                headless=headless,
                launch_args=self._stealth_plan.launch_args,
                proxy=proxy,
            ),
            stealth_hook=stealth_hook,
        )

    def _create_context_options(self) -> BrowserContextOptions:
        context_options = self._stealth_plan.profile.to_context_options()
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

    async def _is_login_form_visible(self, page: Any) -> bool:
        locator = page.locator(self._get_selector("login_form"))
        if await locator.count() == 0:
            return False
        return await locator.first.is_visible()

    async def _raise_if_security_challenge(self, page: Any) -> None:
        title = (await page.title()).strip().lower()
        body_text = (await page.locator("body").inner_text()).strip().lower()
        if any(token in title for token in ("just a moment", "请稍候")):
            raise CaptchaRequiredError("3dbrute is blocked by Cloudflare verification")
        if any(
            token in body_text
            for token in (
                "security verification",
                "执行安全验证",
                "cloudflare",
                "verify you are not a bot",
                "验证您不是自动程序",
            )
        ):
            raise CaptchaRequiredError("3dbrute is blocked by Cloudflare verification")

    async def _wait_for_login_form_ready(self, page: Any) -> None:
        async def check_form() -> bool | None:
            await self._raise_if_security_challenge(page)
            if await self._is_login_form_visible(page):
                return True
            return None

        try:
            await poll_until(
                check_form,
                timeout=min(self._timeout, 10000) / 1000,
                interval=0.2,
            )
        except PollTimeoutError as exc:
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
                raise CaptchaRequiredError(normalized)
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
            error_message = await self._read_login_error(page)
            if error_message is not None:
                raise InvalidCredentialsError(error_message)

            login_form_visible = await self._is_login_form_visible(page)
            has_auth_cookies = await self._has_auth_cookies(context)
            current_url = page.url
            logout_count = await page.locator(self._get_selector("logout_link")).count()
            dashboard_count = await page.locator(self._get_selector("dashboard_marker")).count()

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
                timeout=min(self._timeout, 15000) / 1000,
                interval=0.2,
            )
        except PollTimeoutError as exc:
            raise LoginFailedError(
                "3dbrute login did not complete", reason="login_timeout"
            ) from exc

    async def login(self, credentials: Dict[str, Any]) -> Session:
        username = str(credentials.get("username") or "").strip()
        password = str(credentials.get("password") or "").strip()
        if not username or not password:
            raise InvalidCredentialsError("username and password are required")

        context = None
        page = None

        try:
            await self._browser_manager.start()
            context = await self._browser_manager.new_context(self._create_context_options())
            page = await context.new_page()
            await page.goto(self.LOGIN_URL, wait_until="domcontentloaded")
            await self._wait_for_login_form_ready(page)

            await page.fill(self._get_selector("username_input"), username)
            await page.fill(self._get_selector("password_input"), password)
            await page.click(self._get_selector("login_button"))

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
                metadata={
                    "cookie_domain": ".3dbrute.com",
                    "login_time": datetime.now().isoformat(),
                    "login_url": self.LOGIN_URL,
                    "user_agent": user_agent,
                },
            )
        finally:
            await self._close_page_safely(page)
            await self._close_context_safely(context)

    async def verify(self, session: Session) -> bool:
        if session.is_expired() or not session.cookies:
            return False

        context = None
        page = None

        try:
            await self._browser_manager.start()
            context = await self._browser_manager.new_context(self._create_context_options())
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
            page = await context.new_page()
            await page.goto(self.DASHBOARD_URL, wait_until="domcontentloaded")
            current_url = page.url
            has_auth_cookies = await self._has_auth_cookies(context)
            logout_count = await page.locator(self._get_selector("logout_link")).count()
            dashboard_count = await page.locator(self._get_selector("dashboard_marker")).count()
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

    async def refresh(self, session: Session) -> Session:
        if session.is_expired():
            raise SessionExpiredError("Session has already expired")
        is_valid = await self.verify(session)
        if not is_valid:
            raise SessionExpiredError("Session is no longer valid")
        session.expires_at = datetime.now() + timedelta(days=7)
        session.update_usage()
        return session

    async def logout(self, session: Session) -> bool:
        context = None
        page = None

        try:
            await self._browser_manager.start()
            context = await self._browser_manager.new_context(self._create_context_options())
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
            page = await context.new_page()
            await page.goto(self.LOGOUT_URL, wait_until="domcontentloaded")
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

    async def close(self) -> None:
        await self._browser_manager.close()

    async def __aenter__(self) -> "ThreeDBruteAuthenticator":
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.close()
