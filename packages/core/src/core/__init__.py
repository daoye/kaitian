"""
KaiTian 核心包

提供所有模块共享的核心抽象和数据结构
"""

# 版本信息
from .__version__ import __author__, __email__, __version__

# 配置管理
from .config import (
    BrowserConfig,
    ConfigManager,
    CoreConfig,
    CrawlConfig,
    DatabaseConfig,
    DownloadConfig,
    LlmConfig,
    LogConfig,
    SecurityConfig,
    get_config,
)

# 异常定义
from .exceptions import (
    AuthError,
    BrowserError,
    CaptchaError,
    ConfigError,
    DownloadError,
    KaitianError,
    NetworkError,
    PublishError,
    ResourceError,
    SessionError,
    StorageError,
    TimeoutError,
    ValidationError,
)

# 核心数据模型和接口
from .models import (
    Authenticator,
    BrowserContext,
    Downloader,
    Publisher,
    PublishResult,
    Resource,
    Session,
    SessionGroup,
    Storage,
    ValidationResult,
    Validator,
    Workflow,
)

# 类型定义
from .types import (
    LogLevel,
    PublishTarget,
    ResourceStatus,
    ValidationLevel,
    WorkflowStatus,
    WorkflowStep,
)

# 轮询等待辅助函数
from .wait import PollTimeoutError, poll_until

# 公共 API
__all__ = [
    # 版本信息
    "__version__",
    "__author__",
    "__email__",
    # 类型定义
    "LogLevel",
    "PublishTarget",
    "ResourceStatus",
    "ValidationLevel",
    "WorkflowStep",
    "WorkflowStatus",
    # 异常定义
    "KaitianError",
    "ConfigError",
    "AuthError",
    "BrowserError",
    "DownloadError",
    "ValidationError",
    "PublishError",
    "CaptchaError",
    "SessionError",
    "ResourceError",
    "TimeoutError",
    "NetworkError",
    "StorageError",
    # 配置管理
    "CoreConfig",
    "DatabaseConfig",
    "BrowserConfig",
    "CrawlConfig",
    "DownloadConfig",
    "LlmConfig",
    "LogConfig",
    "SecurityConfig",
    "ConfigManager",
    "get_config",
    # 核心数据模型
    "Resource",
    "Session",
    "SessionGroup",
    "ValidationResult",
    "PublishResult",
    "Workflow",
    # 抽象接口
    "Authenticator",
    "Downloader",
    "Validator",
    "Publisher",
    "BrowserContext",
    "Storage",
    # 轮询等待
    "PollTimeoutError",
    "poll_until",
]
