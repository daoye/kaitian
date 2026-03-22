"""AuthManager 和 Repository 测试."""

import pytest
import tempfile
import os
from datetime import datetime, timedelta

from auth import AuthManager, SessionRepository
from auth.exceptions import SessionNotFoundError, SiteNotSupportedError


class DummyPage:
    def __init__(self) -> None:
        self.goto_calls: list[str] = []

    async def goto(self, url: str) -> None:
        self.goto_calls.append(url)

    async def wait_for_event(self, name: str) -> None:
        return None


class DummyBrowserManager:
    def __init__(self) -> None:
        self.applied_session = None
        self.applied_base_url = None
        self.page = DummyPage()

    async def apply_session(self, session, base_url=None) -> None:
        self.applied_session = session
        self.applied_base_url = base_url

    async def new_page(self):
        return self.page


class TestSessionRepository:
    """测试 SessionRepository."""

    @pytest.fixture
    def repo(self):
        """创建临时仓库."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        repo = SessionRepository(db_path)
        yield repo
        os.unlink(db_path)

    def test_save_and_get(self, repo):
        """测试保存和获取会话."""
        from core.models import Session

        session = Session(
            session_id="test-001",
            site="znzmo",
            account_id="testuser",
            cookies={"session": "abc123"},
            headers={"User-Agent": "Test"},
        )

        repo.save(session)

        # 通过 session_id 获取
        retrieved = repo.get_by_session_id("test-001")
        assert retrieved is not None
        assert retrieved.session_id == "test-001"
        assert retrieved.site == "znzmo"
        assert retrieved.account_id == "testuser"

        # 通过 site + account_id 获取
        retrieved2 = repo.get_by_account("znzmo", "testuser")
        assert retrieved2 is not None
        assert retrieved2.session_id == "test-001"

    def test_delete(self, repo):
        """测试删除会话."""
        from core.models import Session

        session = Session(session_id="test-002", site="znzmo", account_id="testuser2")

        repo.save(session)
        assert repo.delete("test-002") is True
        assert repo.get_by_session_id("test-002") is None
        assert repo.delete("test-002") is False

    def test_list_by_site(self, repo):
        """测试按站点列出会话."""
        from core.models import Session

        # 创建多个会话
        for i in range(3):
            session = Session(session_id=f"test-{i}", site="znzmo", account_id=f"user{i}")
            repo.save(session)

        # 创建不同站点的会话
        session = Session(session_id="test-other", site="other", account_id="user")
        repo.save(session)

        sessions = repo.list_by_site("znzmo")
        assert len(sessions) == 3

    def test_list_all(self, repo):
        """测试列出所有会话."""
        from core.models import Session

        repo.save(Session(session_id="test-a", site="znzmo", account_id="user-a"))
        repo.save(Session(session_id="test-b", site="other", account_id="user-b"))

        sessions = repo.list_all()
        assert len(sessions) == 2


class TestAuthManager:
    """测试 AuthManager."""

    @pytest.fixture
    def manager(self):
        """创建临时管理器."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        repo = SessionRepository(db_path)
        manager = AuthManager(repo)
        yield manager
        os.unlink(db_path)

    def test_register_and_get_authenticator(self, manager):
        """测试注册认证器."""
        from unittest.mock import MagicMock

        auth_mock = MagicMock()
        manager.register_authenticator("test", auth_mock)

        # 验证已注册（通过检查内部字典）
        assert "test" in manager._authenticators

    def test_get_session_not_found(self, manager):
        """测试获取不存在的会话."""
        session = manager.get_session("znzmo", "nonexistent")
        assert session is None

    def test_get_session_by_id(self, manager):
        """测试通过 session_id 获取会话."""
        from core.models import Session

        session = Session(session_id="session-001", site="znzmo", account_id="tester")
        manager._repository.save(session)

        retrieved = manager.get_session_by_id("session-001")
        assert retrieved is not None
        assert retrieved.session_id == "session-001"
        assert retrieved.account_id == "tester"

    def test_get_session_by_id_expired_returns_none(self, manager):
        """测试过期 session_id 查询返回 None."""
        from core.models import Session

        session = Session(
            session_id="session-expired",
            site="znzmo",
            account_id="tester",
            expires_at=datetime.now() - timedelta(minutes=1),
        )
        manager._repository.save(session)

        assert manager.get_session_by_id("session-expired") is None

    def test_login_unsupported_site(self, manager):
        """测试不支持的站点."""
        import asyncio

        with pytest.raises(SiteNotSupportedError):
            asyncio.run(manager.login("unsupported", "user", {}))

    def test_logout_nonexistent_session(self, manager):
        """测试登出不存在的会话."""
        import asyncio

        # 应该返回 True（幂等）
        result = asyncio.run(manager.logout("znzmo", "nonexistent"))
        assert result is True

    def test_open_site_uses_session(self, manager):
        """测试使用指定会话打开目标网站."""
        import asyncio
        from core.models import Session

        session = Session(session_id="session-open", site="znzmo", account_id="tester")
        manager._repository.save(session)
        browser_manager = DummyBrowserManager()

        page = asyncio.run(
            manager.open_site("session-open", "https://example.com", browser_manager)
        )

        assert browser_manager.applied_session is not None
        assert browser_manager.applied_session.session_id == "session-open"
        assert browser_manager.applied_base_url == "https://example.com"
        assert browser_manager.page.goto_calls == ["https://example.com"]
        assert page is browser_manager.page

    def test_open_site_missing_session_raises(self, manager):
        """测试缺失会话时打开网站失败."""
        import asyncio

        browser_manager = DummyBrowserManager()

        with pytest.raises(SessionNotFoundError):
            asyncio.run(
                manager.open_site("missing-session", "https://example.com", browser_manager)
            )

    def test_list_sessions_all_sites(self, manager):
        """测试不指定站点时列出所有会话."""
        from core.models import Session

        manager._repository.save(Session(session_id="session-a", site="znzmo", account_id="a"))
        manager._repository.save(Session(session_id="session-b", site="other", account_id="b"))

        sessions = manager.list_sessions()
        assert len(sessions) == 2
