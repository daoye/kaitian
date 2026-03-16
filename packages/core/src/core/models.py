"""
核心数据模型和接口

定义 KaiTian 项目中的核心数据结构和抽象接口
"""

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncContextManager, Dict, List, Optional, Protocol

from .exceptions import KaitianError
from .types import ResourceStatus


class Resource:
    """资源模型

    表示一个可下载、验证和发布的资源
    """

    def __init__(
        self,
        id: str,
        url: Optional[str] = None,
        local_path: Optional[Path] = None,
        metadata: Optional[Dict[str, Any]] = None,
        status: ResourceStatus = ResourceStatus.PENDING,
    ):
        self.id = id
        self.url = url
        self.local_path = local_path
        self.metadata = metadata or {}
        self.status = status
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def update_status(self, status: ResourceStatus) -> None:
        """更新资源状态"""
        self.status = status
        self.updated_at = datetime.now()

    def add_metadata(self, key: str, value: Any) -> None:
        """添加元数据"""
        self.metadata[key] = value
        self.updated_at = datetime.now()

    def __repr__(self) -> str:
        return f"Resource(id={self.id!r}, status={self.status.value!r})"


class Session:
    """会话模型

    表示一个网站的登录会话状态
    """

    def __init__(
        self,
        session_id: str,
        site: str,
        account_id: str,
        cookies: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None,
        expires_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.session_id = session_id
        self.site = site
        self.account_id = account_id
        self.cookies = cookies or {}
        self.headers = headers or {}
        self.expires_at = expires_at
        self.metadata = metadata or {}
        self.created_at = datetime.now()
        self.last_used = datetime.now()

    def is_expired(self) -> bool:
        """检查会话是否已过期"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

    def update_usage(self) -> None:
        """更新最后使用时间"""
        self.last_used = datetime.now()

    def __repr__(self) -> str:
        return f"Session(session_id={self.session_id!r}, site={self.site!r})"


class SessionGroup:
    """会话组模型

    表示一组相关的会话，通常用于源和目标的映射
    """

    def __init__(
        self,
        name: str,
        source_session: str,
        target_session: str,
        source_sessions: Optional[List[str]] = None,
        target_sessions: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.source_session = source_session
        self.target_session = target_session
        self.source_sessions = source_sessions or []
        self.target_sessions = target_sessions or []
        self.metadata = metadata or {}
        self.created_at = datetime.now()

    def add_source_session(self, session_id: str) -> None:
        """添加源会话"""
        if session_id not in self.source_sessions:
            self.source_sessions.append(session_id)

    def add_target_session(self, session_id: str) -> None:
        """添加目标会话"""
        if session_id not in self.target_sessions:
            self.target_sessions.append(session_id)

    def __repr__(self) -> str:
        return f"SessionGroup(name={self.name!r}, source_session={self.source_session!r}, target_session={self.target_session!r})"


class ValidationResult:
    """验证结果模型"""

    def __init__(
        self,
        is_valid: bool,
        errors: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.is_valid = is_valid
        self.errors = errors or []
        self.warnings = warnings or []
        self.details = details or {}
        self.validated_at = datetime.now()

    def add_error(self, error: str) -> None:
        """添加错误信息"""
        self.errors.append(error)
        self.is_valid = False

    def add_warning(self, warning: str) -> None:
        """添加警告信息"""
        self.warnings.append(warning)

    def __bool__(self) -> bool:
        return self.is_valid


class PublishResult:
    """发布结果模型"""

    def __init__(
        self,
        success: bool,
        url: Optional[str] = None,
        errors: Optional[List[str]] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.success = success
        self.url = url
        self.errors = errors or []
        self.details = details or {}
        self.published_at = datetime.now()

    def add_error(self, error: str) -> None:
        """添加错误信息"""
        self.errors.append(error)
        self.success = False

    def __bool__(self) -> bool:
        return self.success


class Authenticator(ABC):
    """认证器抽象接口

    定义了认证器必须实现的方法
    """

    @abstractmethod
    async def login(self, credentials: Dict[str, Any]) -> Session:
        """执行登录操作

        Args:
            credentials: 认证凭据

        Returns:
            登录成功后的会话对象

        Raises:
            AuthError: 认证失败时抛出
        """
        pass

    @abstractmethod
    async def logout(self, session: Session) -> bool:
        """执行登出操作

        Args:
            session: 要登出的会话

        Returns:
            是否成功登出

        Raises:
            AuthError: 登出失败时抛出
        """
        pass

    @abstractmethod
    async def refresh(self, session: Session) -> Session:
        """刷新会话

        Args:
            session: 要刷新的会话

        Returns:
            刷新后的会话对象

        Raises:
            AuthError: 刷新失败时抛出
        """
        pass

    @abstractmethod
    async def verify(self, session: Session) -> bool:
        """验证会话是否有效

        Args:
            session: 要验证的会话

        Returns:
            会话是否有效
        """
        pass


class Downloader(ABC):
    """下载器抽象接口

    定义了下载器必须实现的方法
    """

    @abstractmethod
    async def download(self, resource: Resource) -> Path:
        """下载资源

        Args:
            resource: 要下载的资源

        Returns:
            下载文件的本地路径

        Raises:
            DownloadError: 下载失败时抛出
        """
        pass

    @abstractmethod
    async def get_file_size(self, url: str) -> int:
        """获取文件大小

        Args:
            url: 文件URL

        Returns:
            文件大小（字节）

        Raises:
            DownloadError: 获取失败时抛出
        """
        pass

    @abstractmethod
    async def is_exists(self, url: str) -> bool:
        """检查URL是否存在

        Args:
            url: 要检查的URL

        Returns:
            URL是否存在
        """
        pass


class Validator(ABC):
    """验证器抽象接口

    定义了验证器必须实现的方法
    """

    @abstractmethod
    async def validate(self, resource: Resource) -> ValidationResult:
        """验证资源

        Args:
            resource: 要验证的资源

        Returns:
            验证结果

        Raises:
            ValidationError: 验证过程中出错时抛出
        """
        pass

    @abstractmethod
    async def get_supported_types(self) -> List[str]:
        """获取支持的资源类型

        Returns:
            支持的资源类型列表
        """
        pass


class Publisher(ABC):
    """发布器抽象接口

    定义了发布器必须实现的方法
    """

    @abstractmethod
    async def publish(self, resource: Resource) -> PublishResult:
        """发布资源

        Args:
            resource: 要发布的资源

        Returns:
            发布结果

        Raises:
            PublishError: 发布失败时抛出
        """
        pass

    @abstractmethod
    async def delete(self, resource_id: str) -> bool:
        """删除已发布的资源

        Args:
            resource_id: 要删除的资源ID

        Returns:
            是否成功删除

        Raises:
            PublishError: 删除失败时抛出
        """
        pass

    @abstractmethod
    async def get_status(self, resource_id: str) -> Dict[str, Any]:
        """获取发布状态

        Args:
            resource_id: 资源ID

        Returns:
            发布状态信息

        Raises:
            PublishError: 获取状态失败时抛出
        """
        pass


class BrowserContext(ABC):
    """浏览器上下文协议

    定义了浏览器上下文必须实现的接口
    """

    @abstractmethod
    async def get_page(self, url: str) -> Any:
        """获取页面

        Args:
            url: 页面URL

        Returns:
            页面对象
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """关闭浏览器上下文"""
        pass

    @abstractmethod
    async def __aenter__(self) -> "BrowserContext":
        """异步进入上下文"""
        pass

    @abstractmethod
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """异步退出上下文"""
        pass


class Storage(ABC):
    """存储抽象接口

    定义了存储器必须实现的方法
    """

    @abstractmethod
    async def save(self, key: str, value: Any) -> None:
        """保存数据

        Args:
            key: 键
            value: 值

        Raises:
            StorageError: 保存失败时抛出
        """
        pass

    @abstractmethod
    async def load(self, key: str, default: Any = None) -> Any:
        """加载数据

        Args:
            key: 键
            default: 默认值

        Returns:
            存储的值或默认值

        Raises:
            StorageError: 加载失败时抛出
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """删除数据

        Args:
            key: 键

        Returns:
            是否成功删除

        Raises:
            StorageError: 删除失败时抛出
        """
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """检查键是否存在

        Args:
            key: 键

        Returns:
            键是否存在
        """
        pass
