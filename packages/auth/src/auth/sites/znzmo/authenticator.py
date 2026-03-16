"""知末网 (znzmo.com) 认证适配器."""

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from core.models import Authenticator, Session
from auth.exceptions import LoginFailedError, CaptchaRequiredError
from auth.types import Credentials, CaptchaOutcome, VerifyResult
from browser import BrowserManager, BrowserLaunchOptions


class ZnzmoAuthenticator(Authenticator):
    """知末网认证适配器."""

    # 知末网相关配置
    BASE_URL = "https://www.znzmo.com"
    LOGIN_URL = "https://www.znzmo.com/login"
    USER_CENTER_URL = "https://www.znzmo.com/personalCenter"

    # 页面选择器（需要根据实际页面调整）
    SELECTORS = {
        "username_input": "input[name='username']",
        "password_input": "input[name='password']",
        "login_button": "button[type='submit']",
        "captcha_image": ".captcha-img",
        "error_message": ".error-message",
        "user_avatar": ".user-avatar",
        "user_name": ".user-name",
    }

    def __init__(self, captcha_solver=None, timeout: int = 30000):
        """初始化.

        Args:
            captcha_solver: 验证码处理器
            timeout: 操作超时时间（毫秒）
        """
        self._browser_manager = BrowserManager()
        self._captcha_solver = captcha_solver
        self._timeout = timeout

    async def login(self, credentials: Dict[str, Any]) -> Session:
        """执行知末网登录.

        Args:
            credentials: 包含 username 和 password 的字典

        Returns:
            登录成功后的 Session 对象

        Raises:
            LoginFailedError: 登录失败
            CaptchaRequiredError: 需要验证码
        """
        username = credentials.get("username")
        password = credentials.get("password")

        if not username or not password:
            raise LoginFailedError(
                "Username and password are required", reason="missing_credentials"
            )

        # 使用浏览器进行登录
        await self._browser_manager.start()
        browser = self._browser_manager
        try:
            page = await browser.new_page()

            # 访问登录页面
            await page.goto(self.LOGIN_URL, wait_until="networkidle")

            # 填写用户名
            await page.fill(self.SELECTORS["username_input"], username)

            # 填写密码
            await page.fill(self.SELECTORS["password_input"], password)

            # 检查是否需要验证码
            captcha_element = await page.query_selector(self.SELECTORS["captcha_image"])
            if captcha_element:
                if not self._captcha_solver:
                    raise CaptchaRequiredError("CAPTCHA required but no solver configured")

                # 处理验证码
                outcome = await self._solve_captcha(page)
                if outcome.status == "failed":
                    raise LoginFailedError(
                        "CAPTCHA solving failed", reason="captcha_failed", details=outcome.data
                    )

            # 点击登录按钮
            await page.click(self.SELECTORS["login_button"])

            # 等待登录结果
            try:
                # 等待页面跳转或错误提示
                await page.wait_for_load_state("networkidle", timeout=self._timeout)
            except Exception:
                pass

            # 检查登录错误
            error_element = await page.query_selector(self.SELECTORS["error_message"])
            if error_element:
                error_text = await error_element.text_content()
                raise LoginFailedError(
                    f"Login failed: {error_text}",
                    reason="invalid_credentials",
                    details={"error_text": error_text},
                )

            # 检查是否登录成功（通过查找用户头像或用户名）
            user_element = await page.query_selector(
                f"{self.SELECTORS['user_avatar']}, {self.SELECTORS['user_name']}"
            )
            if not user_element:
                raise LoginFailedError(
                    "Login may have failed - user indicator not found", reason="unknown"
                )

            # 提取 cookies
            cookies = await browser.get_cookies()
            cookie_dict = {c["name"]: c["value"] for c in cookies}

            # 创建会话
            session = Session(
                session_id=str(uuid.uuid4()),
                site="znzmo",
                account_id=username,
                cookies=cookie_dict,
                headers={"User-Agent": await page.evaluate("navigator.userAgent")},
                expires_at=datetime.now() + timedelta(days=7),  # 默认7天过期
                metadata={"login_time": datetime.now().isoformat(), "login_url": self.LOGIN_URL},
            )

            return session

        finally:
            pass  # BrowserManager 会在最后统一关闭

    async def _solve_captcha(self, page) -> CaptchaOutcome:
        """解决验证码."""
        if not self._captcha_solver:
            return CaptchaOutcome(status="manual_required")

        # 截图验证码区域
        captcha_element = await page.query_selector(self.SELECTORS["captcha_image"])
        if not captcha_element:
            return CaptchaOutcome(status="not_present")

        # 这里应该调用验证码求解器
        # 暂时返回需要手动处理
        return CaptchaOutcome(status="manual_required")

    async def logout(self, session: Session) -> bool:
        """执行登出.

        Args:
            session: 要登出的会话

        Returns:
            是否成功登出
        """
        await self._browser_manager.start()
        browser = self._browser_manager
        try:
            page = await browser.new_page()

            # 设置 cookies
            await browser.set_cookies(
                [
                    {"name": k, "value": v, "domain": ".znzmo.com"}
                    for k, v in session.cookies.items()
                ]
            )

            # 访问登出链接（需要确认实际URL）
            await page.goto(f"{self.BASE_URL}/logout")

            return True
        except Exception:
            return False
        finally:
            pass  # BrowserManager 会在最后统一关闭

    async def refresh(self, session: Session) -> Session:
        """刷新会话.

        知末网不支持真正的刷新，这里只验证会话是否仍然有效。
        如果无效，抛出异常要求重新登录。

        Args:
            session: 要刷新的会话

        Returns:
            更新后的会话

        Raises:
            LoginFailedError: 会话已失效需要重新登录
        """
        is_valid = await self.verify(session)
        if not is_valid:
            raise LoginFailedError("Session expired, please re-login", reason="session_expired")

        # 更新过期时间
        session.expires_at = datetime.now() + timedelta(days=7)
        return session

    async def verify(self, session: Session) -> bool:
        """验证会话是否有效.

        通过访问个人中心页面并检查是否需要登录来判断。

        Args:
            session: 要验证的会话

        Returns:
            会话是否有效
        """
        if session.is_expired():
            return False

        await self._browser_manager.start()
        browser = self._browser_manager
        try:
            page = await browser.new_page()

            # 设置 cookies
            await browser.set_cookies(
                [
                    {"name": k, "value": v, "domain": ".znzmo.com"}
                    for k, v in session.cookies.items()
                ]
            )

            # 访问个人中心
            await page.goto(self.USER_CENTER_URL, wait_until="domcontentloaded")

            # 检查是否被重定向到登录页
            current_url = page.url
            if "/login" in current_url:
                return False

            # 检查是否存在用户标识
            user_element = await page.query_selector(
                f"{self.SELECTORS['user_avatar']}, {self.SELECTORS['user_name']}"
            )

            return user_element is not None

        except Exception:
            return False
        finally:
            pass  # BrowserManager 会在最后统一关闭

    async def close(self) -> None:
        """关闭浏览器管理器."""
        await self._browser_manager.close()

    async def __aenter__(self) -> "ZnzmoAuthenticator":
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.close()
