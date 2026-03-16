"""AuthManager 和 Repository 测试."""

import pytest
import tempfile
import os

from auth import AuthManager, SessionRepository
from auth.exceptions import SessionNotFoundError, SiteNotSupportedError


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
