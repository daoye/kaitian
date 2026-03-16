"""
异常体系

定义 KaiTian 项目中使用的所有异常类型
"""

from typing import Any, Optional


class KaitianError(Exception):
    """KaiTian 基础异常类"""
    def __init__(self, message: str, *, error_code: Optional[str] = None, details: Optional[dict[str, Any]] = None):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}


class ConfigError(KaitianError):
    """配置相关异常"""
    pass


class AuthError(KaitianError):
    """认证相关异常"""
    pass


class BrowserError(KaitianError):
    """浏览器相关异常"""
    pass


class DownloadError(KaitianError):
    """下载相关异常"""
    pass


class ValidationError(KaitianError):
    """验证相关异常"""
    pass


class PublishError(KaitianError):
    """发布相关异常"""
    pass


class CaptchaError(AuthError):
    """验证码相关异常"""
    pass


class SessionError(KaitianError):
    """会话相关异常"""
    pass


class ResourceError(KaitianError):
    """资源相关异常"""
    pass


class TimeoutError(KaitianError):
    """超时相关异常"""
    pass


class NetworkError(KaitianError):
    """网络相关异常"""
    pass


class StorageError(KaitianError):
    """存储相关异常"""
    pass