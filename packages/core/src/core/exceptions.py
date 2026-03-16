"""
异常体系

定义 KaiTian 项目中使用的所有异常类型
"""

from typing import Any, Optional


class KaitianError(Exception):
    def __init__(
        self,
        message: str,
        *,
        error_code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}


class ConfigError(KaitianError):
    pass


class AuthError(KaitianError):
    pass


class BrowserError(KaitianError):
    pass


class DownloadError(KaitianError):
    pass


class ValidationError(KaitianError):
    pass


class PublishError(KaitianError):
    pass


class CaptchaError(AuthError):
    pass


class SessionError(KaitianError):
    pass


class ResourceError(KaitianError):
    pass


class TimeoutError(KaitianError):
    pass


class NetworkError(KaitianError):
    pass


class StorageError(KaitianError):
    pass
