"""
核心类型定义

包含所有模块共享的基础类型和枚举
"""

from enum import Enum, StrEnum


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


class WorkflowStep(StrEnum):
    """通用下载步骤枚举。

    适用于任意网站的下载流程，按执行顺序排列：
    pending → fetching → meta_extracted → file_downloaded
    → previews_downloaded → processing → completed
    """
    PENDING = "pending"
    FETCHING = "fetching"
    META_EXTRACTED = "meta_extracted"
    FILE_DOWNLOADED = "file_downloaded"
    PREVIEWS_DOWNLOADED = "previews_downloaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

    @classmethod
    def valid_steps(cls) -> list[str]:
        return [s.value for s in cls if s.value not in ("completed", "failed")]


class WorkflowStatus(StrEnum):
    """工作流状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
