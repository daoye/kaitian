"""
核心类型定义

包含所有模块共享的基础类型和枚举
"""

from enum import Enum


class ResourceStatus(Enum):
    """资源状态枚举"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    DOWNLOADED = "downloaded"
    VALIDATING = "validating"
    VALIDATED = "validated"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"


class ValidationLevel(Enum):
    """验证级别枚举"""
    NONE = "none"
    BASIC = "basic"
    STRICT = "strict"
    CUSTOM = "custom"


class PublishTarget(Enum):
    """发布目标枚举"""
    NONE = "none"
    LOCAL = "local"
    REMOTE = "remote"
    MULTIPLE = "multiple"


class LogLevel(Enum):
    """日志级别枚举"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"