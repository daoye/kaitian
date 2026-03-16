"""auth 异常定义."""

from core.exceptions import AuthError as CoreAuthError


class AuthError(CoreAuthError):
    """认证相关错误."""

    pass


class SessionNotFoundError(AuthError):
    """会话未找到."""

    pass


class SessionExpiredError(AuthError):
    """会话已过期."""

    pass


class InvalidCredentialsError(AuthError):
    """凭据无效."""

    pass


class LoginFailedError(AuthError):
    """登录失败."""

    def __init__(self, message: str, reason: str = "", details: dict = None):
        super().__init__(message)
        self.reason = reason
        self.details = details or {}


class CaptchaRequiredError(AuthError):
    """需要验证码."""

    pass


class SessionStorageError(AuthError):
    """会话存储错误."""

    pass


class SiteNotSupportedError(AuthError):
    """站点不支持."""

    pass
