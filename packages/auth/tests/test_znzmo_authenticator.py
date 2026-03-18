"""知末网认证适配器生产级测试.

验证生命周期管理、Session契约、异常映射、验证码处理等生产级能力。
"""

import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from auth.exceptions import (
    CaptchaRequiredError,
    InvalidCredentialsError,
    LoginFailedError,
    SessionExpiredError,
)
from auth.sites.znzmo.authenticator import ZnzmoAuthenticator
from auth.types import CaptchaOutcome
from core.models import Session


class TestLifecycleManagement:
    """测试生命周期管理 - 确保资源可靠关闭."""

    @pytest.mark.asyncio
    async def test_page_closed_after_successful_login(self):
        """成功登录后 page 必须被关闭."""
        authenticator = ZnzmoAuthenticator()
        mock_page = AsyncMock()
        mock_context = AsyncMock()
        mock_browser = AsyncMock()

        # 模拟成功登录流程
        with patch.object(authenticator, "_browser_manager") as mock_manager:
            mock_manager.start = AsyncMock()
            mock_manager.new_context = AsyncMock(return_value=mock_context)
            mock_context.new_page = AsyncMock(return_value=mock_page)
            mock_context.close = AsyncMock()
            mock_manager.close = AsyncMock()

            # 模拟页面元素 - 成功登录场景
            mock_page.goto = AsyncMock()
            mock_page.fill = AsyncMock()
            mock_page.click = AsyncMock()
            mock_page.wait_for_load_state = AsyncMock()
            mock_page.evaluate = AsyncMock(return_value="Mozilla/5.0")
            mock_page.close = AsyncMock()

            # query_selector 调用顺序: 1.验证码检查 2.错误信息检查 3.用户标识检查
            mock_user_element = AsyncMock()  # 找到用户标识，表示登录成功
            mock_page.query_selector = AsyncMock(
                side_effect=[
                    None,  # 无验证码
                    None,  # 无错误信息
                    mock_user_element,  # 找到用户标识
                ]
            )

            mock_context.cookies = AsyncMock(
                return_value=[{"name": "session_id", "value": "test123", "domain": ".znzmo.com"}]
            )

            credentials = {"username": "test_user", "password": "test_pass"}
            session = await authenticator.login(credentials)

            # 验证 page 被关闭
            mock_page.close.assert_called_once()
            # 验证 context 被关闭
            mock_context.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_page_closed_on_login_failure(self):
        """登录失败时 page 必须被关闭."""
        authenticator = ZnzmoAuthenticator()
        mock_page = AsyncMock()
        mock_context = AsyncMock()

        with patch.object(authenticator, "_browser_manager") as mock_manager:
            mock_manager.start = AsyncMock()
            mock_manager.new_context = AsyncMock(return_value=mock_context)
            mock_context.new_page = AsyncMock(return_value=mock_page)
            mock_context.close = AsyncMock()
            mock_manager.close = AsyncMock()

            mock_page.goto = AsyncMock()
            mock_page.fill = AsyncMock()
            mock_page.query_selector = AsyncMock(return_value=None)
            mock_page.click = AsyncMock()
            mock_page.wait_for_load_state = AsyncMock()
            mock_page.close = AsyncMock()

            # 模拟登录错误（显示错误信息）
            mock_error_element = AsyncMock()
            mock_error_element.text_content = AsyncMock(return_value="密码错误")
            mock_page.query_selector = AsyncMock(
                side_effect=[
                    None,  # 无验证码
                    mock_error_element,  # 有错误信息
                ]
            )

            credentials = {"username": "test_user", "password": "wrong_pass"}

            with pytest.raises(LoginFailedError):
                await authenticator.login(credentials)

            # 即使失败，page 也必须被关闭
            mock_page.close.assert_called_once()
            mock_context.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_browser_manager_closed_on_authenticator_close(self):
        """认证器关闭时必须关闭 browser_manager."""
        authenticator = ZnzmoAuthenticator()

        with patch.object(authenticator, "_browser_manager") as mock_manager:
            mock_manager.close = AsyncMock()

            await authenticator.close()

            mock_manager.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager_cleanup(self):
        """异步上下文管理器必须正确清理资源."""
        authenticator = ZnzmoAuthenticator()

        with patch.object(authenticator, "_browser_manager") as mock_manager:
            mock_manager.close = AsyncMock()

            async with authenticator:
                pass

            mock_manager.close.assert_called_once()


class TestSessionContract:
    """测试 Session 契约对齐."""

    def _setup_successful_login_mocks(self, mock_manager, mock_page, mock_context):
        """设置成功登录的 mock 配置."""
        mock_manager.start = AsyncMock()
        mock_manager.new_context = AsyncMock(return_value=mock_context)
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.close = AsyncMock()
        mock_manager.close = AsyncMock()

        mock_page.goto = AsyncMock()
        mock_page.fill = AsyncMock()
        mock_page.click = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value="Mozilla/5.0")
        mock_page.close = AsyncMock()

        # query_selector 调用顺序: 1.验证码检查 2.错误信息检查 3.用户标识检查
        mock_user_element = AsyncMock()  # 找到用户标识，表示登录成功
        mock_page.query_selector = AsyncMock(
            side_effect=[
                None,  # 无验证码
                None,  # 无错误信息
                mock_user_element,  # 找到用户标识
            ]
        )

        mock_context.cookies = AsyncMock(
            return_value=[{"name": "session_id", "value": "test123", "domain": ".znzmo.com"}]
        )

    @pytest.mark.asyncio
    async def test_session_site_is_short_key(self):
        """Session.site 应该是短键 'znzmo' 而非域名."""
        authenticator = ZnzmoAuthenticator()
        mock_page = AsyncMock()
        mock_context = AsyncMock()

        with patch.object(authenticator, "_browser_manager") as mock_manager:
            self._setup_successful_login_mocks(mock_manager, mock_page, mock_context)

            credentials = {"username": "test_user", "password": "test_pass"}
            session = await authenticator.login(credentials)

            # site 应该是短键
            assert session.site == "znzmo"

    @pytest.mark.asyncio
    async def test_session_includes_cookie_domain_in_metadata(self):
        """Session.metadata 必须包含 cookie_domain 供 browser 使用."""
        authenticator = ZnzmoAuthenticator()
        mock_page = AsyncMock()
        mock_context = AsyncMock()

        with patch.object(authenticator, "_browser_manager") as mock_manager:
            self._setup_successful_login_mocks(mock_manager, mock_page, mock_context)

            credentials = {"username": "test_user", "password": "test_pass"}
            session = await authenticator.login(credentials)

            # metadata 必须包含 cookie_domain
            assert "cookie_domain" in session.metadata
            assert session.metadata["cookie_domain"] == ".znzmo.com"

    @pytest.mark.asyncio
    async def test_session_includes_required_metadata(self):
        """Session.metadata 应包含必要的追踪信息."""
        authenticator = ZnzmoAuthenticator()
        mock_page = AsyncMock()
        mock_context = AsyncMock()

        with patch.object(authenticator, "_browser_manager") as mock_manager:
            self._setup_successful_login_mocks(mock_manager, mock_page, mock_context)

            credentials = {"username": "test_user", "password": "test_pass"}
            session = await authenticator.login(credentials)

            # 验证必要字段
            assert "login_time" in session.metadata
            assert "login_url" in session.metadata
            assert "user_agent" in session.metadata


class TestExceptionMapping:
    """测试异常正确映射 - 不吞异常."""

    @pytest.mark.asyncio
    async def test_missing_credentials_raises_invalid_credentials(self):
        """缺失凭据应抛出 InvalidCredentialsError."""
        authenticator = ZnzmoAuthenticator()

        with pytest.raises(InvalidCredentialsError) as exc_info:
            await authenticator.login({})

        assert (
            "username" in str(exc_info.value).lower() or "password" in str(exc_info.value).lower()
        )

    @pytest.mark.asyncio
    async def test_empty_username_raises_invalid_credentials(self):
        """空用户名应抛出 InvalidCredentialsError."""
        authenticator = ZnzmoAuthenticator()

        with pytest.raises(InvalidCredentialsError):
            await authenticator.login({"username": "", "password": "pass"})

    @pytest.mark.asyncio
    async def test_invalid_credentials_raises_login_failed(self):
        """页面显示错误信息时应抛出 LoginFailedError."""
        authenticator = ZnzmoAuthenticator()
        mock_page = AsyncMock()
        mock_context = AsyncMock()

        with patch.object(authenticator, "_browser_manager") as mock_manager:
            mock_manager.start = AsyncMock()
            mock_manager.new_context = AsyncMock(return_value=mock_context)
            mock_context.new_page = AsyncMock(return_value=mock_page)
            mock_context.close = AsyncMock()
            mock_manager.close = AsyncMock()

            mock_page.goto = AsyncMock()
            mock_page.fill = AsyncMock()
            mock_page.click = AsyncMock()
            mock_page.wait_for_load_state = AsyncMock()
            mock_page.close = AsyncMock()

            # 模拟错误信息元素
            mock_error_element = AsyncMock()
            mock_error_element.text_content = AsyncMock(return_value="用户名或密码错误")
            mock_page.query_selector = AsyncMock(
                side_effect=[
                    None,  # 无验证码
                    mock_error_element,  # 有错误信息
                ]
            )

            credentials = {"username": "test_user", "password": "wrong_pass"}

            with pytest.raises(LoginFailedError) as exc_info:
                await authenticator.login(credentials)

            assert exc_info.value.reason == "invalid_credentials"
            assert "error_text" in exc_info.value.details

    @pytest.mark.asyncio
    async def test_browser_failure_raises_login_failed(self):
        """browser 失败应映射为 LoginFailedError 而非原始异常."""
        authenticator = ZnzmoAuthenticator()

        with patch.object(authenticator, "_browser_manager") as mock_manager:
            mock_manager.start = AsyncMock(side_effect=Exception("Browser launch failed"))

            with pytest.raises(LoginFailedError) as exc_info:
                await authenticator.login({"username": "test", "password": "test"})

            assert (
                "browser" in str(exc_info.value).lower() or "launch" in str(exc_info.value).lower()
            )

    @pytest.mark.asyncio
    async def test_verify_returns_false_on_invalid_session(self):
        """验证无效会话应返回 False，不吞异常."""
        authenticator = ZnzmoAuthenticator()
        session = Session(
            session_id="test_session",
            site="znzmo",
            account_id="test_user",
            cookies={"session_id": "invalid"},
            expires_at=datetime.now() + timedelta(days=7),
            metadata={"cookie_domain": ".znzmo.com"},
        )

        mock_page = AsyncMock()
        mock_context = AsyncMock()

        with patch.object(authenticator, "_browser_manager") as mock_manager:
            mock_manager.start = AsyncMock()
            mock_manager.new_context = AsyncMock(return_value=mock_context)
            mock_context.new_page = AsyncMock(return_value=mock_page)
            mock_context.close = AsyncMock()
            mock_manager.close = AsyncMock()

            # 模拟重定向到登录页（会话无效）
            mock_page.goto = AsyncMock()
            mock_page.url = "https://www.znzmo.com/login"
            mock_page.close = AsyncMock()

            result = await authenticator.verify(session)

            # 应该返回 False 而非抛出异常
            assert result is False
            mock_page.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_raises_on_browser_failure(self):
        """验证时 browser 失败应抛出异常而非返回 False."""
        authenticator = ZnzmoAuthenticator()
        session = Session(
            session_id="test_session",
            site="znzmo",
            account_id="test_user",
            cookies={"session_id": "test"},
            expires_at=datetime.now() + timedelta(days=7),
            metadata={"cookie_domain": ".znzmo.com"},
        )

        with patch.object(authenticator, "_browser_manager") as mock_manager:
            mock_manager.start = AsyncMock(side_effect=Exception("Browser crashed"))

            # 基础设施失败应该抛出异常
            with pytest.raises(Exception):
                await authenticator.verify(session)


class TestCaptchaHandling:
    """测试验证码处理."""

    @pytest.mark.asyncio
    async def test_captcha_detected_without_solver_raises_captcha_required(self):
        """检测到验证码但没有 solver 应抛出 CaptchaRequiredError."""
        authenticator = ZnzmoAuthenticator(captcha_solver=None)
        mock_page = AsyncMock()
        mock_context = AsyncMock()

        with patch.object(authenticator, "_browser_manager") as mock_manager:
            mock_manager.start = AsyncMock()
            mock_manager.new_context = AsyncMock(return_value=mock_context)
            mock_context.new_page = AsyncMock(return_value=mock_page)
            mock_context.close = AsyncMock()
            mock_manager.close = AsyncMock()

            mock_page.goto = AsyncMock()
            mock_page.fill = AsyncMock()
            mock_page.click = AsyncMock()
            mock_page.close = AsyncMock()

            # 模拟检测到验证码
            mock_captcha_element = AsyncMock()
            mock_page.query_selector = AsyncMock(return_value=mock_captcha_element)

            credentials = {"username": "test_user", "password": "test_pass"}

            with pytest.raises(CaptchaRequiredError):
                await authenticator.login(credentials)

            mock_page.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_captcha_solver_returns_manual_required_raises_captcha_required(self):
        """solver 返回 manual_required 应抛出 CaptchaRequiredError."""
        mock_solver = AsyncMock()
        mock_solver.solve = AsyncMock(
            return_value=CaptchaOutcome(
                status="manual_required", data={"message": "请手动输入验证码"}
            )
        )

        authenticator = ZnzmoAuthenticator(captcha_solver=mock_solver)
        mock_page = AsyncMock()
        mock_context = AsyncMock()

        with patch.object(authenticator, "_browser_manager") as mock_manager:
            mock_manager.start = AsyncMock()
            mock_manager.new_context = AsyncMock(return_value=mock_context)
            mock_context.new_page = AsyncMock(return_value=mock_page)
            mock_context.close = AsyncMock()
            mock_manager.close = AsyncMock()

            mock_page.goto = AsyncMock()
            mock_page.fill = AsyncMock()
            mock_page.click = AsyncMock()
            mock_page.close = AsyncMock()

            # 模拟检测到验证码
            mock_captcha_element = AsyncMock()
            mock_page.query_selector = AsyncMock(return_value=mock_captcha_element)

            credentials = {"username": "test_user", "password": "test_pass"}

            with pytest.raises(CaptchaRequiredError) as exc_info:
                await authenticator.login(credentials)

            # 应该包含详细信息
            assert hasattr(exc_info.value, "details") or "manual" in str(exc_info.value).lower()
            mock_page.close.assert_called_once()


class TestLogoutAndRefresh:
    """测试登出和刷新."""

    @pytest.mark.asyncio
    async def test_logout_closes_resources(self):
        """登出必须关闭所有资源."""
        authenticator = ZnzmoAuthenticator()
        session = Session(
            session_id="test_session",
            site="znzmo",
            account_id="test_user",
            cookies={"session_id": "test"},
            metadata={"cookie_domain": ".znzmo.com"},
        )

        mock_page = AsyncMock()
        mock_context = AsyncMock()

        with patch.object(authenticator, "_browser_manager") as mock_manager:
            mock_manager.start = AsyncMock()
            mock_manager.new_context = AsyncMock(return_value=mock_context)
            mock_context.new_page = AsyncMock(return_value=mock_page)
            mock_context.close = AsyncMock()
            mock_manager.close = AsyncMock()

            mock_page.goto = AsyncMock()
            mock_page.close = AsyncMock()

            await authenticator.logout(session)

            mock_page.close.assert_called_once()
            mock_context.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_raises_session_expired_on_invalid(self):
        """刷新无效会话应抛出 SessionExpiredError."""
        authenticator = ZnzmoAuthenticator()
        session = Session(
            session_id="test_session",
            site="znzmo",
            account_id="test_user",
            cookies={"session_id": "invalid"},
            expires_at=datetime.now() + timedelta(days=7),
            metadata={"cookie_domain": ".znzmo.com"},
        )

        mock_page = AsyncMock()
        mock_context = AsyncMock()

        with patch.object(authenticator, "_browser_manager") as mock_manager:
            mock_manager.start = AsyncMock()
            mock_manager.new_context = AsyncMock(return_value=mock_context)
            mock_context.new_page = AsyncMock(return_value=mock_page)
            mock_context.close = AsyncMock()
            mock_manager.close = AsyncMock()

            mock_page.goto = AsyncMock()
            mock_page.url = "https://www.znzmo.com/login"  # 重定向到登录页
            mock_page.close = AsyncMock()

            with pytest.raises(SessionExpiredError):
                await authenticator.refresh(session)

            mock_page.close.assert_called_once()
