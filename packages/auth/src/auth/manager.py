"""AuthManager 实现."""

from typing import Any, Dict, Optional

from browser import BrowserManager
from core.models import Authenticator, Session
from .exceptions import AuthError, SessionNotFoundError, SiteNotSupportedError
from .repository import SessionRepository


class AuthManager:
    """认证管理器."""

    def __init__(self, repository: SessionRepository):
        self._repository = repository
        self._authenticators: Dict[str, Authenticator] = {}

    def register_authenticator(self, site: str, authenticator: Authenticator) -> None:
        """注册站点认证器."""
        self._authenticators[site] = authenticator

    async def login(self, site: str, account_id: str, credentials: Dict[str, Any]) -> Session:
        """执行登录.

        Args:
            site: 站点标识
            account_id: 账号标识
            credentials: 登录凭据

        Returns:
            登录成功后的会话

        Raises:
            SiteNotSupportedError: 站点未注册
            LoginFailedError: 登录失败
        """
        authenticator = self._authenticators.get(site)
        if not authenticator:
            raise SiteNotSupportedError(f"Site '{site}' is not supported")

        # 执行登录
        session = await authenticator.login(credentials)
        session.site = site
        session.account_id = account_id

        # 保存会话
        self._repository.save(session)

        return session

    def get_session(self, site: str, account_id: str) -> Optional[Session]:
        """获取会话（自动检查过期）.

        Args:
            site: 站点标识
            account_id: 账号标识

        Returns:
            会话对象，不存在或已过期返回 None
        """
        session = self._repository.get_by_account(site, account_id)
        if session and session.is_expired():
            return None
        return session

    def get_session_by_id(self, session_id: str) -> Optional[Session]:
        """通过会话 ID 获取会话（自动检查过期）."""
        session = self._repository.get_by_session_id(session_id)
        if session and session.is_expired():
            return None
        return session

    async def verify(self, site: str, account_id: str) -> bool:
        """验证会话是否有效.

        Args:
            site: 站点标识
            account_id: 账号标识

        Returns:
            会话是否有效
        """
        session = self.get_session(site, account_id)
        if not session:
            return False

        authenticator = self._authenticators.get(site)
        if not authenticator:
            return False

        return await authenticator.verify(session)

    async def refresh(self, site: str, account_id: str) -> Optional[Session]:
        """刷新会话.

        Args:
            site: 站点标识
            account_id: 账号标识

        Returns:
            刷新后的会话，失败返回 None
        """
        session = self._repository.get_by_account(site, account_id)
        if not session:
            raise SessionNotFoundError(f"Session not found for {site}/{account_id}")

        authenticator = self._authenticators.get(site)
        if not authenticator:
            raise SiteNotSupportedError(f"Site '{site}' is not supported")

        try:
            refreshed = await authenticator.refresh(session)
            self._repository.save(refreshed)
            return refreshed
        except AuthError:
            return None

    async def logout(self, site: str, account_id: str) -> bool:
        """执行登出.

        Args:
            site: 站点标识
            account_id: 账号标识

        Returns:
            是否成功登出
        """
        session = self._repository.get_by_account(site, account_id)
        if not session:
            return True

        authenticator = self._authenticators.get(site)
        if authenticator:
            try:
                await authenticator.logout(session)
            except AuthError:
                pass  # 即使远程登出失败也删除本地会话

        return self._repository.delete(session.session_id)

    def list_sessions(self, site: str | None = None) -> list[Session]:
        """列出会话，可按站点过滤."""
        if site is None:
            return self._repository.list_all()
        return self._repository.list_by_site(site)

    async def open_site(self, session_id: str, url: str, browser_manager: BrowserManager) -> Any:
        """使用指定会话打开目标网站."""
        session = self.get_session_by_id(session_id)
        if not session:
            raise SessionNotFoundError(f"Session not found: {session_id}")

        await browser_manager.apply_session(session, base_url=url)
        page = await browser_manager.new_page()
        await page.goto(url)
        return page
