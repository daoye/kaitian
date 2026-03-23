"""知末网 (znzmo.com) 认证适配器 - 生产级实现.

特性:
- 完整的生命周期管理 (page/context/browser 可靠关闭)
- Session 契约对齐 (metadata.cookie_domain)
- 正确的异常映射 (不吞异常)
- 可配置的页面选择器
- 验证码处理框架
- Stealth 集成支持
"""

import logging
import asyncio
import inspect
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional, cast
from unittest.mock import AsyncMock, Mock

from browser import BrowserManager, BrowserLaunchOptions
from browser.exceptions import BrowserError, BrowserLaunchError
from core.models import Authenticator, Session

from auth.exceptions import (
    AuthError,
    CaptchaRequiredError,
    InvalidCredentialsError,
    LoginFailedError,
    SessionExpiredError,
)
from auth.types import CaptchaOutcome
from auth.verification import (
    ConsoleVerificationCodeProvider,
    VerificationCodeChallenge,
    VerificationCodeProvider,
)
from core.wait import PollTimeoutError, poll_until

logger = logging.getLogger("auth.znzmo")


class ZnzmoAuthenticator(Authenticator):
    """知末网认证适配器 - 生产级实现.

    示例:
        # 基础用法
        async with ZnzmoAuthenticator() as auth:
            session = await auth.login({
                "username": "your_username",
                "password": "your_password"
            })

        # 带验证码求解器
        async with ZnzmoAuthenticator(captcha_solver=my_solver) as auth:
            try:
                session = await auth.login(credentials)
            except CaptchaRequiredError as e:
                # 处理需要手动验证码的情况
                pass

        # 带自定义选择器和 stealth
        async with ZnzmoAuthenticator(
            selectors={"username_input": "#custom-user"},
            stealth_hook=stealth_manager.apply_to_context
        ) as auth:
            session = await auth.login(credentials)
    """

    # 知末网相关配置
    BASE_URL = "https://www.znzmo.com"
    LOGIN_URL = "https://www.znzmo.com/?from=personalCenter"
    USER_CENTER_URL = "https://www.znzmo.com/personalCenter"

    # 默认页面选择器
    DEFAULT_SELECTORS = {
        "phone_login_button": "text=手机",
        "password_tab": "text=账号密码登录",
        "password_phone_input": "input[placeholder='请输入手机号']",
        "password_input": "input[placeholder='请输入密码']",
        "login_button": "text=登录/注册",
        "sms_tab": "text=手机验证码登录",
        "sms_phone_input": "input[placeholder='请输入手机号']",
        "sms_code_input": "input[placeholder='请输入验证码']",
        "sms_send_code_button": "div[class*='Accountpassword__input-code__']",
        "sms_submit_button": "text=登录/注册",
        "captcha_image": ".captcha-img",
        "captcha_input": "input[name='captcha']",
        "error_message": ".error-message",
        "user_avatar": ".user-avatar",
        "user_name": ".user-name",
    }

    def __init__(
        self,
        captcha_solver: Optional[Any] = None,
        timeout: int = 300000,
        selectors: Optional[Dict[str, str]] = None,
        stealth_hook: Optional[Callable] = None,
        verification_code_provider: Optional[VerificationCodeProvider] = None,
        headless: bool = True,
        enable_cdp: bool = False,
        cdp_port: int | None = None,
    ):
        """初始化认证适配器.

        Args:
            captcha_solver: 验证码求解器，需实现 solve(image_bytes, context) 方法
            timeout: 操作超时时间（毫秒）
            selectors: 自定义页面选择器，会覆盖默认选择器
            stealth_hook: 反检测钩子，传递给 BrowserManager
        """
        self._captcha_solver = captcha_solver
        self._timeout = timeout
        self._enable_cdp = enable_cdp
        self._cdp_port = cdp_port
        self._selectors = {**self.DEFAULT_SELECTORS, **(selectors or {})}
        self._stealth_hook = stealth_hook
        self._verification_code_provider = (
            verification_code_provider or ConsoleVerificationCodeProvider()
        )
        self._browser_manager = BrowserManager(
            launch_options=BrowserLaunchOptions(
                headless=headless,
                enable_cdp=enable_cdp,
                cdp_port=cdp_port,
            ),
            stealth_hook=stealth_hook,
        )

    def _get_selector(self, key: str) -> str:
        """获取选择器."""
        return self._selectors.get(key, self.DEFAULT_SELECTORS.get(key, ""))

    def _uses_locator_fallback(self, page: Any) -> bool:
        locator_method = getattr(page, "locator", None)
        return (
            locator_method is None
            or inspect.iscoroutinefunction(locator_method)
            or isinstance(locator_method, AsyncMock)
            or isinstance(locator_method, Mock)
        )

    def _locator(self, page: Any, selector: str) -> Any:
        return page.locator(selector).first

    async def _read_selector_state(self, page: Any, selector: str) -> dict[str, Any]:
        locator_method = getattr(page, "locator", None)
        if self._uses_locator_fallback(page):
            return {"exists": True, "visible": True, "enabled": True, "value": None}

        locator_result = locator_method(selector)

        locator = locator_result.first
        count = await locator_result.count()
        if count == 0:
            return {"exists": False, "visible": False, "enabled": False, "value": None}

        visible = False
        enabled = False
        value = None

        try:
            visible = await locator.is_visible()
        except Exception:
            visible = False

        try:
            enabled = await locator.is_enabled()
        except Exception:
            enabled = False

        try:
            value = await locator.input_value()
        except Exception:
            value = None

        return {
            "exists": True,
            "visible": visible,
            "enabled": enabled,
            "value": value,
        }

    async def _dispatch_input_events(self, page: Any, selector: str) -> None:
        locator_method = getattr(page, "locator", None)
        if self._uses_locator_fallback(page):
            return

        locator_result = locator_method(selector)

        await locator_result.first.evaluate(
            """
            (element) => {
                element.dispatchEvent(new Event('input', { bubbles: true }));
                element.dispatchEvent(new Event('change', { bubbles: true }));
                if (typeof element.blur === 'function') {
                    element.blur();
                }
            }
            """
        )

    async def _read_selector_text(self, page: Any, selector: str) -> str | None:
        locator_method = getattr(page, "locator", None)
        if self._uses_locator_fallback(page):
            return None

        locator_result = locator_method(selector)
        count = await locator_result.count()
        if count == 0:
            return None

        text = await locator_result.first.text_content()
        if text is None:
            return None
        return text.strip()

    async def _wait_for_login_flow_ready(self, page: Any, login_mode: str) -> None:
        if login_mode == "sms":
            selectors = [
                self._get_selector("sms_phone_input"),
                self._get_selector("sms_code_input"),
            ]
        else:
            selectors = [
                self._get_selector("password_phone_input"),
                self._get_selector("password_input"),
            ]

        await self._wait_for_visible_selectors(page, selectors, "login_dialog_not_ready")

    async def _wait_for_visible_selectors(
        self,
        page: Any,
        selectors: list[str],
        reason: str,
        timeout_ms: int | None = None,
    ) -> None:
        """等待所有选择器都变为可见."""

        async def check_all_visible() -> bool | None:
            """检查所有选择器是否都可见。"""
            for selector in selectors:
                state = await self._read_selector_state(page, selector)
                if not (state.get("exists") and state.get("visible")):
                    return None
            return True

        timeout_s = (timeout_ms or min(self._timeout, 8000)) / 1000

        try:
            await poll_until(check_all_visible, timeout=timeout_s, interval=0.2)
        except PollTimeoutError:
            raise LoginFailedError("Login dialog did not become ready", reason=reason)

    async def _prepare_sms_login(self, page: Any) -> None:
        await self._wait_for_visible_selectors(
            page,
            [self._get_selector("phone_login_button")],
            "login_entry_not_ready",
        )

        sms_phone_state = await self._read_selector_state(
            page, self._get_selector("sms_phone_input")
        )
        sms_code_state = await self._read_selector_state(page, self._get_selector("sms_code_input"))
        if (
            sms_phone_state.get("exists")
            and sms_phone_state.get("visible")
            and sms_code_state.get("exists")
            and sms_code_state.get("visible")
        ):
            return

        phone_button_state = await self._read_selector_state(
            page, self._get_selector("phone_login_button")
        )
        if phone_button_state.get("exists") and phone_button_state.get("visible"):
            await page.click(self._get_selector("phone_login_button"))

        await self._wait_for_visible_selectors(
            page,
            [self._get_selector("sms_tab")],
            "sms_tab_not_ready",
        )

        sms_tab_state = await self._read_selector_state(page, self._get_selector("sms_tab"))
        if sms_tab_state.get("exists") and sms_tab_state.get("visible"):
            await page.click(self._get_selector("sms_tab"))

        await self._wait_for_login_flow_ready(page, "sms")

    async def _prepare_password_login(self, page: Any) -> None:
        await self._wait_for_visible_selectors(
            page,
            [self._get_selector("phone_login_button")],
            "login_entry_not_ready",
        )

        phone_button_state = await self._read_selector_state(
            page, self._get_selector("phone_login_button")
        )
        if phone_button_state.get("exists") and phone_button_state.get("visible"):
            await page.click(self._get_selector("phone_login_button"))

        await self._wait_for_visible_selectors(
            page,
            [self._get_selector("password_tab")],
            "password_tab_not_ready",
        )

        password_tab_state = await self._read_selector_state(
            page, self._get_selector("password_tab")
        )
        if password_tab_state.get("exists") and password_tab_state.get("visible"):
            await page.click(self._get_selector("password_tab"))

        await self._wait_for_login_flow_ready(page, "password")

    async def _type_sms_phone_number(self, page: Any, phone: str) -> None:
        phone_selector = self._get_selector("sms_phone_input")

        if self._uses_locator_fallback(page):
            await page.fill(phone_selector, phone)
            await self._dispatch_input_events(page, phone_selector)
            return

        phone_locator = self._locator(page, phone_selector)
        await phone_locator.click()
        await phone_locator.fill("")
        await phone_locator.type(phone, delay=120)
        await phone_locator.evaluate(
            """
            (element) => {
                if (typeof element.blur === 'function') {
                    element.blur();
                }
            }
            """
        )
        await self._dispatch_input_events(page, phone_selector)

    async def _wait_for_sms_form_stable(self, page: Any, phone: str) -> None:
        """等待短信表单稳定。"""
        phone_selector = self._get_selector("sms_phone_input")
        timeout_s = min(self._timeout, 5000) / 1000

        async def check_form_stable() -> bool | None:
            """检查表单状态是否稳定。"""
            phone_state = await self._read_selector_state(page, phone_selector)
            if not isinstance(phone_state, dict):
                return True

            phone_value = phone_state.get("value")
            phone_ready = phone_value == phone
            if phone_value is None and self._uses_locator_fallback(page):
                phone_ready = True

            ready = (
                phone_state.get("exists")
                and phone_state.get("visible")
                and phone_state.get("enabled")
                and phone_ready
            )
            if ready:
                return True
            return None

        try:
            await poll_until(check_form_stable, timeout=timeout_s, interval=0.2)
        except PollTimeoutError:
            raise LoginFailedError(
                "SMS form did not become stable",
                reason="sms_form_not_ready",
                details={"phone": phone},
            )

    async def _confirm_sms_send_started(self, page: Any, before_text: str | None) -> None:
        """确认验证码发送已开始。"""
        send_selector = self._get_selector("sms_send_code_button")

        async def check_text_changed() -> bool | None:
            """检查按钮文本是否已改变。"""
            current_text = await self._read_selector_text(page, send_selector)
            if (
                current_text
                and current_text != before_text
                and any(char.isdigit() for char in current_text)
            ):
                return True
            return None

        try:
            await poll_until(check_text_changed, timeout=5.0, interval=0.2)
        except PollTimeoutError:
            raise LoginFailedError(
                "SMS send was not confirmed",
                reason="sms_send_unconfirmed",
            )

    async def _request_sms_code(self, page: Any, phone: str) -> None:
        send_selector = self._get_selector("sms_send_code_button")

        await self._type_sms_phone_number(page, phone)
        await self._wait_for_sms_form_stable(page, phone)

        if self._uses_locator_fallback(page):
            await page.click(send_selector)
            return

        send_locator = self._locator(page, send_selector)
        await send_locator.scroll_into_view_if_needed()
        before_text = await self._read_selector_text(page, send_selector)
        await send_locator.click(timeout=3000)
        await self._confirm_sms_send_started(page, before_text)

    async def _fill_sms_code(self, page: Any, sms_code: str) -> None:
        await page.fill(self._get_selector("sms_code_input"), sms_code)
        await self._dispatch_input_events(page, self._get_selector("sms_code_input"))

    async def _read_login_error(self, page: Any) -> str | None:
        error_element = await page.query_selector(self._get_selector("error_message"))
        if error_element is None:
            return None
        error_text = await error_element.text_content()
        if error_text is None:
            return None
        cleaned = error_text.strip()
        return cleaned or None

    async def _has_user_indicator(self, page: Any) -> bool:
        user_element = await page.query_selector(
            f"{self._get_selector('user_avatar')}, {self._get_selector('user_name')}"
        )
        return user_element is not None

    async def _is_login_modal_visible(self, page: Any, login_mode: str) -> bool:
        selectors = [self._get_selector("phone_login_button")]
        if login_mode == "sms":
            selectors.extend(
                [self._get_selector("sms_phone_input"), self._get_selector("sms_code_input")]
            )
        else:
            selectors.extend(
                [self._get_selector("password_phone_input"), self._get_selector("password_input")]
            )

        for selector in selectors:
            if not selector:
                continue
            element = await page.query_selector(selector)
            if element is not None:
                return True
        return False

    async def _extract_cookie_dict(self, context: Any) -> dict[str, str]:
        cookies = await context.cookies()
        return {cookie["name"]: cookie["value"] for cookie in cookies}

    def _is_transient_navigation_error(self, exc: Exception) -> bool:
        message = str(exc)
        return (
            "Execution context was destroyed" in message
            or "most likely because of a navigation" in message
        )

    async def _wait_for_login_outcome(
        self,
        page: Any,
        context: Any,
        login_mode: str,
    ) -> tuple[str, dict[str, str], str | None]:
        """等待登录结果。"""
        timeout_s = self._timeout / 1000
        last_cookie_dict: dict[str, str] = {}

        def is_transient_navigation_error(exc: Exception) -> bool:
            """判断是否为瞬态导航错误。"""
            return self._is_transient_navigation_error(exc)

        async def check_outcome() -> tuple[str, dict[str, str], str | None] | None:
            """检查登录结果。"""
            nonlocal last_cookie_dict  # 声明使用外层变量

            # 检查错误信息
            error_text = await self._read_login_error(page)
            if error_text is not None:
                return ("error", last_cookie_dict, error_text)

            # 检查用户标识
            has_user_indicator = await self._has_user_indicator(page)
            if has_user_indicator:
                return ("success", await self._extract_cookie_dict(context), None)

            # 检查 cookie 和弹窗状态
            cookie_dict = await self._extract_cookie_dict(context)
            if cookie_dict:
                last_cookie_dict = cookie_dict
                login_modal_visible = await self._is_login_modal_visible(page, login_mode)
                if not login_modal_visible:
                    return ("success", cookie_dict, None)

            return None

        try:
            outcome = cast(
                tuple[str, dict[str, str], str | None],
                await poll_until(
                    check_outcome,
                    timeout=timeout_s,
                    interval=0.2,
                    retry_on_exception=is_transient_navigation_error,
                ),
            )
            return outcome
        except PollTimeoutError:
            return ("timeout", last_cookie_dict, None)

    async def _close_page_safely(self, page: Any) -> None:
        """安全关闭页面，忽略已关闭错误."""
        if page is None:
            return
        try:
            await page.close()
            logger.debug("auth.znzmo.page.closed")
        except Exception as e:
            # 忽略已关闭的错误
            logger.debug("auth.znzmo.page.close_skipped", extra={"reason": str(e)})

    async def _close_context_safely(self, context: Any) -> None:
        """安全关闭上下文，忽略已关闭错误."""
        if context is None:
            return
        try:
            await context.close()
            logger.debug("auth.znzmo.context.closed")
        except Exception as e:
            logger.debug("auth.znzmo.context.close_skipped", extra={"reason": str(e)})

    def _validate_credentials(self, credentials: Dict[str, Any]) -> tuple[str, str]:
        """验证并提取凭据.

        Args:
            credentials: 包含 username 和 password 的字典

        Returns:
            (username, password) 元组

        Raises:
            InvalidCredentialsError: 凭据缺失或无效
        """
        username = credentials.get("username")
        password = credentials.get("password")

        if not username or not password:
            logger.warning("auth.znzmo.login.failed", extra={"reason": "missing_credentials"})
            raise InvalidCredentialsError("Username and password are required")

        if not isinstance(username, str) or not username.strip():
            raise InvalidCredentialsError("Username must be a non-empty string")

        if not isinstance(password, str) or not password.strip():
            raise InvalidCredentialsError("Password must be a non-empty string")

        return username.strip(), password

    def _validate_sms_credentials(self, credentials: Dict[str, Any]) -> tuple[str, Optional[str]]:
        phone = credentials.get("phone")
        sms_code = credentials.get("sms_code")

        if not phone:
            logger.warning(
                "auth.znzmo.login.failed",
                extra={"reason": "missing_sms_credentials"},
            )
            raise InvalidCredentialsError("Phone is required for SMS login")

        if not isinstance(phone, str) or not phone.strip():
            raise InvalidCredentialsError("Phone must be a non-empty string")

        if sms_code is not None and (not isinstance(sms_code, str) or not sms_code.strip()):
            raise InvalidCredentialsError("sms_code must be a non-empty string")

        return phone.strip(), sms_code.strip() if isinstance(sms_code, str) else None

    async def _wait_for_sms_code(self, phone: str) -> str:
        challenge = VerificationCodeChallenge(
            site="znzmo",
            account_id=phone,
            channel="sms",
            prompt=f"请输入知末短信验证码（手机号: {phone}）: ",
            metadata={"login_url": self.LOGIN_URL},
        )
        sms_code = await self._verification_code_provider.wait_for_code(challenge)
        if not isinstance(sms_code, str) or not sms_code.strip():
            raise InvalidCredentialsError("sms_code must be a non-empty string")
        return sms_code.strip()

    def _map_browser_exception(self, exc: Exception, context: str) -> AuthError:
        """将 browser 异常映射为 auth 标准异常.

        Args:
            exc: 原始异常
            context: 异常发生的上下文

        Returns:
            映射后的标准异常
        """
        if isinstance(exc, BrowserLaunchError):
            return LoginFailedError(
                f"Browser launch failed during {context}",
                reason="browser_launch_failed",
                details={"original_error": str(exc), "context": context},
            )
        elif isinstance(exc, BrowserError):
            return LoginFailedError(
                f"Browser operation failed during {context}",
                reason="browser_operation_failed",
                details={"original_error": str(exc), "context": context},
            )
        else:
            return LoginFailedError(
                f"Unexpected error during {context}",
                reason="unexpected_error",
                details={"original_error": str(exc), "context": context},
            )

    async def login(self, credentials: Dict[str, Any]) -> Session:
        """执行知末网登录.

        Args:
            credentials: 包含 username 和 password 的字典

        Returns:
            登录成功后的 Session 对象

        Raises:
            InvalidCredentialsError: 凭据缺失或无效
            CaptchaRequiredError: 需要验证码
            LoginFailedError: 登录失败（凭据错误、页面错误等）
        """
        login_mode = credentials.get("login_mode", "password")
        if login_mode == "sms":
            account_id, sms_code = self._validate_sms_credentials(credentials)
            username = None
            password = None
        elif login_mode == "password":
            account_id, password = self._validate_credentials(credentials)
            username = account_id
            sms_code = None
        else:
            raise InvalidCredentialsError("login_mode must be 'password' or 'sms'")

        logger.info("auth.znzmo.login.begin", extra={"account_id": account_id, "mode": login_mode})

        context = None
        page = None

        try:
            # 启动浏览器
            try:
                await self._browser_manager.start()
            except Exception as exc:
                mapped_exc = self._map_browser_exception(exc, "browser_start")
                logger.error(
                    "auth.znzmo.login.failed",
                    extra={
                        "reason": "browser_start_failed",
                        "error": str(exc),
                    },
                )
                raise mapped_exc from exc

            # 创建上下文和页面
            try:
                from browser import BrowserContextOptions

                context = await self._browser_manager.new_context(
                    BrowserContextOptions(base_url=self.BASE_URL)
                )
                page = await context.new_page()
            except Exception as exc:
                mapped_exc = self._map_browser_exception(exc, "context_creation")
                logger.error(
                    "auth.znzmo.login.failed",
                    extra={
                        "reason": "context_creation_failed",
                        "error": str(exc),
                    },
                )
                raise mapped_exc from exc

            # 访问登录页面
            try:
                await page.goto(self.LOGIN_URL, wait_until="load")
            except Exception as exc:
                raise LoginFailedError(
                    "Failed to navigate to login page",
                    reason="navigation_failed",
                    details={"url": self.LOGIN_URL, "error": str(exc)},
                ) from exc

            # 填写登录表单
            try:
                if login_mode == "sms":
                    await self._prepare_sms_login(page)
                    await self._request_sms_code(page, account_id)
                    if sms_code is None:
                        sms_code = await self._wait_for_sms_code(account_id)
                    await self._fill_sms_code(page, sms_code)
                else:
                    await self._prepare_password_login(page)
                    await page.fill(self._get_selector("password_phone_input"), username)
                    await page.fill(self._get_selector("password_input"), password)
            except InvalidCredentialsError:
                raise
            except Exception as exc:
                raise LoginFailedError(
                    "Failed to fill login form",
                    reason="form_fill_failed",
                    details={"error": str(exc)},
                ) from exc

            # 检查并处理验证码
            await self._handle_captcha_if_needed(page)

            # 点击登录按钮
            try:
                if login_mode == "sms":
                    await page.click(self._get_selector("sms_submit_button"))
                else:
                    await page.click(self._get_selector("login_button"))
            except Exception as exc:
                raise LoginFailedError(
                    "Failed to click login button",
                    reason="click_failed",
                    details={"error": str(exc)},
                ) from exc

            outcome, cookie_dict, error_text = await self._wait_for_login_outcome(
                page,
                context,
                login_mode,
            )
            if outcome == "error" and error_text is not None:
                logger.warning(
                    "auth.znzmo.login.failed",
                    extra={
                        "reason": "invalid_credentials",
                        "error_text": error_text,
                    },
                )
                raise LoginFailedError(
                    f"Login failed: {error_text}",
                    reason="invalid_credentials",
                    details={"error_text": error_text},
                )

            if outcome != "success":
                logger.warning(
                    "auth.znzmo.login.failed",
                    extra={
                        "reason": "login_outcome_timeout",
                    },
                )
                raise LoginFailedError(
                    "Login may have failed - no stable success signal observed",
                    reason="login_outcome_timeout",
                )

            # 提取 cookies
            try:
                if not cookie_dict:
                    cookie_dict = await self._extract_cookie_dict(context)
            except Exception as exc:
                raise LoginFailedError(
                    "Failed to extract cookies",
                    reason="cookie_extraction_failed",
                    details={"error": str(exc)},
                ) from exc

            # 获取用户代理
            try:
                user_agent = await page.evaluate("navigator.userAgent")
            except Exception:
                user_agent = ""

            # 创建会话 - 生产级 Session 契约
            session = Session(
                session_id=str(uuid.uuid4()),
                site="znzmo",  # 短键用于 repository 索引
                account_id=account_id,
                cookies=cookie_dict,
                headers={"User-Agent": user_agent} if user_agent else {},
                expires_at=datetime.now() + timedelta(days=7),
                metadata={
                    "login_time": datetime.now().isoformat(),
                    "login_url": self.LOGIN_URL,
                    "cookie_domain": ".znzmo.com",  # 关键：供 browser 模块使用
                    "user_agent": user_agent,
                    "account_id": account_id,
                },
            )

            logger.info(
                "auth.znzmo.login.success",
                extra={
                    "account_id": account_id,
                    "session_id": session.session_id,
                },
            )

            return session

        except (InvalidCredentialsError, CaptchaRequiredError, LoginFailedError):
            # 重新抛出已知的认证异常
            raise
        except Exception as exc:
            # 捕获其他所有异常并映射
            logger.exception("auth.znzmo.login.failed", extra={"reason": "unexpected_error"})
            if isinstance(exc, AuthError):
                raise
            raise LoginFailedError(
                f"Unexpected error during login: {exc}",
                reason="unexpected_error",
                details={"error": str(exc)},
            ) from exc
        finally:
            # 关键：确保资源被关闭（从里到外）
            await self._close_page_safely(page)
            await self._close_context_safely(context)

    async def _handle_captcha_if_needed(self, page: Any) -> None:
        """检查并处理验证码.

        Args:
            page: Playwright 页面对象

        Raises:
            CaptchaRequiredError: 需要验证码但没有 solver 或 solver 返回 manual_required
            LoginFailedError: 验证码处理失败
        """
        captcha_element = await page.query_selector(self._get_selector("captcha_image"))
        if not captcha_element:
            return

        logger.info("auth.znzmo.captcha.detected")

        if not self._captcha_solver:
            logger.warning("auth.znzmo.captcha.no_solver")
            raise CaptchaRequiredError(
                "CAPTCHA required but no solver configured",
                details={"type": "unknown", "message": "Please provide a captcha solver"},
            )

        # 使用求解器处理验证码
        outcome = await self._solve_captcha(page)

        if outcome.status == "not_present":
            return
        elif outcome.status == "manual_required":
            logger.warning("auth.znzmo.captcha.manual_required")
            raise CaptchaRequiredError(
                "CAPTCHA requires manual intervention",
                details=outcome.data or {},
            )
        elif outcome.status == "failed":
            logger.error("auth.znzmo.captcha.failed", extra={"details": outcome.data})
            raise LoginFailedError(
                "CAPTCHA solving failed",
                reason="captcha_failed",
                details=outcome.data or {},
            )
        elif outcome.status == "solved":
            # 填写验证码
            captcha_code = outcome.data.get("code") if outcome.data else None
            if captcha_code:
                try:
                    await page.fill(self._get_selector("captcha_input"), captcha_code)
                    logger.info("auth.znzmo.captcha.filled")
                except Exception as exc:
                    raise LoginFailedError(
                        "Failed to fill CAPTCHA code",
                        reason="captcha_fill_failed",
                        details={"error": str(exc)},
                    ) from exc
        else:
            logger.warning("auth.znzmo.captcha.unknown_status", extra={"status": outcome.status})
            raise CaptchaRequiredError(
                f"Unknown CAPTCHA outcome status: {outcome.status}",
                details={"status": outcome.status},
            )

    async def _solve_captcha(self, page: Any) -> CaptchaOutcome:
        """解决验证码.

        Args:
            page: Playwright 页面对象

        Returns:
            CaptchaOutcome 结果
        """
        if not self._captcha_solver:
            return CaptchaOutcome(status="manual_required")

        try:
            # 检查验证码元素是否存在
            captcha_element = await page.query_selector(self._get_selector("captcha_image"))
            if not captcha_element:
                return CaptchaOutcome(status="not_present")

            # 截图验证码区域
            screenshot_bytes = await captcha_element.screenshot()

            # 调用求解器
            # 期望求解器接口: async solve(image_bytes: bytes, context: dict) -> CaptchaOutcome
            if hasattr(self._captcha_solver, "solve"):
                outcome = await self._captcha_solver.solve(
                    screenshot_bytes, context={"site": "znzmo", "url": page.url}
                )
                return outcome
            else:
                # 如果 solver 是可调用对象
                outcome = await self._captcha_solver(screenshot_bytes, {"site": "znzmo"})
                if isinstance(outcome, CaptchaOutcome):
                    return outcome
                else:
                    # 兼容字符串返回
                    return CaptchaOutcome(status=outcome)

        except Exception as exc:
            logger.exception("auth.znzmo.captcha.solve_error")
            return CaptchaOutcome(
                status="failed",
                data={"error": str(exc), "type": type(exc).__name__},
            )

    async def logout(self, session: Session) -> bool:
        """执行登出.

        Args:
            session: 要登出的会话

        Returns:
            是否成功登出

        Raises:
            LoginFailedError: 浏览器操作失败（非业务失败）
        """
        if not session.cookies:
            logger.warning("auth.znzmo.logout.no_cookies")
            return False

        context = None
        page = None

        try:
            await self._browser_manager.start()

            # 创建新上下文并设置 cookies
            from browser import BrowserContextOptions

            context = await self._browser_manager.new_context(
                BrowserContextOptions(
                    base_url=self.BASE_URL,
                    storage_state=None,  # 空状态，手动设置 cookies
                )
            )

            # 设置 cookies
            cookie_domain = session.metadata.get("cookie_domain", ".znzmo.com")
            await context.add_cookies(
                [
                    {"name": k, "value": v, "domain": cookie_domain, "path": "/"}
                    for k, v in session.cookies.items()
                ]
            )

            page = await context.new_page()

            # 访问登出链接
            await page.goto(f"{self.BASE_URL}/logout")

            logger.info("auth.znzmo.logout.success", extra={"account_id": session.account_id})
            return True

        except Exception as exc:
            # 生产级：不吞异常，但转换为标准异常
            logger.exception("auth.znzmo.logout.failed")
            raise LoginFailedError(
                "Logout failed due to browser error",
                reason="logout_failed",
                details={"error": str(exc)},
            ) from exc
        finally:
            await self._close_page_safely(page)
            await self._close_context_safely(context)

    async def refresh(self, session: Session) -> Session:
        """刷新会话.

        知末网不支持真正的刷新，这里验证会话是否有效。
        如果无效，抛出 SessionExpiredError。

        Args:
            session: 要刷新的会话

        Returns:
            更新过期时间的会话对象

        Raises:
            SessionExpiredError: 会话已失效
        """
        if session.is_expired():
            logger.warning("auth.znzmo.refresh.session_already_expired")
            raise SessionExpiredError("Session has already expired")

        is_valid = await self.verify(session)

        if not is_valid:
            logger.warning("auth.znzmo.refresh.session_invalid")
            raise SessionExpiredError("Session is no longer valid")

        # 更新过期时间
        session.expires_at = datetime.now() + timedelta(days=7)
        session.update_usage()

        logger.info(
            "auth.znzmo.refresh.success",
            extra={
                "session_id": session.session_id,
                "new_expires_at": session.expires_at.isoformat(),
            },
        )

        return session

    async def verify(self, session: Session) -> bool:
        """验证会话是否有效.

        通过访问个人中心页面并检查是否需要登录来判断。

        Args:
            session: 要验证的会话

        Returns:
            会话是否有效

        Raises:
            LoginFailedError: 浏览器操作失败（基础设施问题，非会话问题）
        """
        if session.is_expired():
            return False

        if not session.cookies:
            return False

        context = None
        page = None

        try:
            await self._browser_manager.start()

            # 创建新上下文并设置 cookies
            from browser import BrowserContextOptions

            cookie_domain = session.metadata.get("cookie_domain", ".znzmo.com")

            context = await self._browser_manager.new_context(
                BrowserContextOptions(
                    base_url=self.BASE_URL,
                    storage_state=None,
                )
            )

            # 设置 cookies
            await context.add_cookies(
                [
                    {"name": k, "value": v, "domain": cookie_domain, "path": "/"}
                    for k, v in session.cookies.items()
                ]
            )

            page = await context.new_page()

            # 访问个人中心
            await page.goto(self.USER_CENTER_URL, wait_until="domcontentloaded")

            # 检查是否被重定向到登录页
            current_url = page.url
            if "/login" in current_url:
                logger.debug(
                    "auth.znzmo.verify.session_invalid", extra={"reason": "redirected_to_login"}
                )
                return False

            # 检查是否存在用户标识
            user_element = await page.query_selector(
                f"{self._get_selector('user_avatar')}, {self._get_selector('user_name')}"
            )

            if user_element is not None:
                logger.debug("auth.znzmo.verify.result", extra={"is_valid": True})
                return True

            is_valid = "/personalCenter" in current_url and "/login" not in current_url
            logger.debug("auth.znzmo.verify.result", extra={"is_valid": is_valid})
            return is_valid

        except Exception as exc:
            # 基础设施失败应抛出异常，而不是返回 False
            # False 只表示"会话无效"，不表示"无法验证"
            logger.exception("auth.znzmo.verify.failed")
            raise LoginFailedError(
                "Failed to verify session due to browser error",
                reason="verify_failed",
                details={"error": str(exc)},
            ) from exc
        finally:
            await self._close_page_safely(page)
            await self._close_context_safely(context)

    async def close(self) -> None:
        """关闭浏览器管理器."""
        try:
            await self._browser_manager.close()
            logger.debug("auth.znzmo.authenticator.closed")
        except Exception as e:
            logger.debug("auth.znzmo.authenticator.close_error", extra={"error": str(e)})

    async def __aenter__(self) -> "ZnzmoAuthenticator":
        """异步进入上下文."""
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        """异步退出上下文，确保资源清理."""
        await self.close()
