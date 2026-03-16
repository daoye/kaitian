"""
KaiTian 核心包

提供所有模块共享的核心抽象和数据结构
"""

# 版本信息
from .__version__ import __author__, __email__, __version__

# 类型定义
from .types import (
    LogLevel,
    PublishTarget,
    ResourceStatus,
    ValidationLevel,
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

# 配置管理
from .config import (
    BrowserConfig,
    ConfigManager,
    CoreConfig,
    DatabaseConfig,
    DownloadConfig,
    LogConfig,
    SecurityConfig,
    get_config,
)

# 核心数据模型和接口
from .models import (
    Authenticator,
    BrowserContext,
    Downloader,
    Publisher,
    Resource,
    Session,
    SessionGroup,
    Storage,
    Validator,
    ValidationResult,
    PublishResult,
)

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
    "DownloadConfig",
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
    
    # 抽象接口
    "Authenticator",
    "Downloader",
    "Validator",
    "Publisher",
    "BrowserContext",
    "Storage",
]
