"""
核心模型单元测试
"""

import pytest
from datetime import datetime, timedelta

from core.models import (
    PublishResult,
    Resource,
    Session,
    SessionGroup,
    ValidationResult,
)
from core.types import ResourceStatus


class TestResource:
    """测试 Resource 模型"""
    
    def test_resource_creation(self):
        """测试 Resource 创建"""
        resource = Resource(
            id="test-1",
            url="https://example.com/test.jpg",
            metadata={"type": "image", "size": 1024}
        )
        
        assert resource.id == "test-1"
        assert resource.url == "https://example.com/test.jpg"
        assert resource.local_path is None
        assert resource.metadata == {"type": "image", "size": 1024}
        assert resource.status == ResourceStatus.PENDING
        assert isinstance(resource.created_at, datetime)
        assert isinstance(resource.updated_at, datetime)
    
    def test_resource_status_update(self):
        """测试 Resource 状态更新"""
        resource = Resource(id="test-2")
        original_updated_at = resource.updated_at
        
        # 稍等片刻以确保时间差
        import time
        time.sleep(0.01)
        
        resource.update_status(ResourceStatus.DOWNLOADING)
        
        assert resource.status == ResourceStatus.DOWNLOADING
        assert resource.updated_at > original_updated_at
    
    def test_resource_add_metadata(self):
        """测试 Resource 添加元数据"""
        resource = Resource(id="test-3")
        original_updated_at = resource.updated_at
        
        # 稍等片刻以确保时间差
        import time
        time.sleep(0.01)
        
        resource.add_metadata("author", "test_user")
        
        assert resource.metadata["author"] == "test_user"
        assert resource.updated_at > original_updated_at
    
    def test_resource_repr(self):
        """测试 Resource 字符串表示"""
        resource = Resource(id="test-4", status=ResourceStatus.DOWNLOADED)
        repr_str = repr(resource)
        
        assert "Resource" in repr_str
        assert "test-4" in repr_str
        assert "downloaded" in repr_str
    
    @pytest.mark.parametrize("status", ResourceStatus)
    def test_resource_all_statuses(self, status):
        """测试 Resource 所有状态"""
        resource = Resource(id="test-5", status=status)
        assert resource.status == status


class TestSession:
    """测试 Session 模型"""
    
    def test_session_creation(self):
        """测试 Session 创建"""
        session = Session(
            session_id="session-1",
            site="example.com",
            account_id="user123",
            cookies={"session": "abc123"},
            headers={"User-Agent": "test"}
        )
        
        assert session.session_id == "session-1"
        assert session.site == "example.com"
        assert session.account_id == "user123"
        assert session.cookies == {"session": "abc123"}
        assert session.headers == {"User-Agent": "test"}
        assert session.expires_at is None
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.last_used, datetime)
    
    def test_session_expiration(self):
        """测试 Session 过期检查"""
        # 未过期的会话
        future_time = datetime.now() + timedelta(hours=1)
        session1 = Session(
            session_id="session-2",
            site="example.com",
            account_id="user123",
            expires_at=future_time
        )
        assert not session1.is_expired()
        
        # 已过期的会话
        past_time = datetime.now() - timedelta(hours=1)
        session2 = Session(
            session_id="session-3",
            site="example.com",
            account_id="user123",
            expires_at=past_time
        )
        assert session2.is_expired()
        
        # 没有过期时间的会话
        session3 = Session(
            session_id="session-4",
            site="example.com",
            account_id="user123"
        )
        assert not session3.is_expired()
    
    def test_session_update_usage(self):
        """测试 Session 更新使用时间"""
        session = Session(
            session_id="session-5",
            site="example.com",
            account_id="user123"
        )
        original_last_used = session.last_used
        
        # 稍等片刻以确保时间差
        import time
        time.sleep(0.01)
        
        session.update_usage()
        
        assert session.last_used > original_last_used
    
    def test_session_repr(self):
        """测试 Session 字符串表示"""
        session = Session(
            session_id="session-6",
            site="example.com",
            account_id="user123"
        )
        repr_str = repr(session)
        
        assert "Session" in repr_str
        assert "session-6" in repr_str
        assert "example.com" in repr_str


class TestSessionGroup:
    """测试 SessionGroup 模型"""
    
    def test_session_group_creation(self):
        """测试 SessionGroup 创建"""
        group = SessionGroup(
            name="test-group",
            source_session="source-1",
            target_session="target-1"
        )
        
        assert group.name == "test-group"
        assert group.source_session == "source-1"
        assert group.target_session == "target-1"
        assert group.source_sessions == []
        assert group.target_sessions == []
        assert isinstance(group.created_at, datetime)
    
    def test_session_group_add_sessions(self):
        """测试 SessionGroup 添加会话"""
        group = SessionGroup(
            name="test-group-2",
            source_session="source-1",
            target_session="target-1"
        )
        
        # 添加源会话
        group.add_source_session("source-2")
        assert "source-2" in group.source_sessions
        assert len(group.source_sessions) == 1
        
        # 重复添加不会重复记录
        group.add_source_session("source-2")
        assert len(group.source_sessions) == 1
        
        # 添加目标会话
        group.add_target_session("target-2")
        assert "target-2" in group.target_sessions
        assert len(group.target_sessions) == 1
    
    def test_session_group_repr(self):
        """测试 SessionGroup 字符串表示"""
        group = SessionGroup(
            name="test-group-3",
            source_session="source-1",
            target_session="target-1"
        )
        repr_str = repr(group)
        
        assert "SessionGroup" in repr_str
        assert "test-group-3" in repr_str
        assert "source-1" in repr_str
        assert "target-1" in repr_str


class TestValidationResult:
    """测试 ValidationResult 模型"""
    
    def test_validation_result_creation_valid(self):
        """测试创建有效的 ValidationResult"""
        result = ValidationResult(is_valid=True)
        
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []
        assert result.details == {}
        assert isinstance(result.validated_at, datetime)
        assert bool(result) is True
    
    def test_validation_result_creation_invalid(self):
        """测试创建无效的 ValidationResult"""
        errors = ["File format not supported", "File too large"]
        result = ValidationResult(is_valid=False, errors=errors)
        
        assert result.is_valid is False
        assert result.errors == errors
        assert bool(result) is False
    
    def test_validation_result_add_error(self):
        """测试 ValidationResult 添加错误"""
        result = ValidationResult(is_valid=True)
        
        result.add_error("New error")
        
        assert not result.is_valid
        assert "New error" in result.errors
    
    def test_validation_result_add_warning(self):
        """测试 ValidationResult 添加警告"""
        result = ValidationResult(is_valid=True)
        
        result.add_warning("Quality warning")
        
        assert result.is_valid  # 警告不影响有效性
        assert "Quality warning" in result.warnings


class TestPublishResult:
    """测试 PublishResult 模型"""
    
    def test_publish_result_creation_success(self):
        """测试创建成功的 PublishResult"""
        result = PublishResult(
            success=True,
            url="https://example.com/published/123"
        )
        
        assert result.success is True
        assert result.url == "https://example.com/published/123"
        assert result.errors == []
        assert isinstance(result.published_at, datetime)
        assert bool(result) is True
    
    def test_publish_result_creation_failure(self):
        """测试创建失败的 PublishResult"""
        errors = ["Upload failed", "Server error"]
        result = PublishResult(success=False, errors=errors)
        
        assert result.success is False
        assert result.errors == errors
        assert bool(result) is False
    
    def test_publish_result_add_error(self):
        """测试 PublishResult 添加错误"""
        result = PublishResult(success=True)
        
        result.add_error("New error")
        
        assert not result.success
        assert "New error" in result.errors